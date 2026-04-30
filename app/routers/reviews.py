from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func

from app.models.reviews import Review as ReviewModel
from app.schemas import Review as ReviewSchema, ReviewCreate
from app.models.products import Product as ProductModel

from app.models.users import User as UserModel
from app.auth import get_current_admin             #----authentification----#
from app.auth import get_current_buyer

from sqlalchemy.ext.asyncio import AsyncSession

from app.db_depends import get_async_db


router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)

@router.get("/", response_model=list[ReviewSchema], status_code=status.HTTP_200_OK)
async def get_all_reviews(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех активных отзывов.
    """
    reviews_result = await db.scalars(
        select(ReviewModel).where(ReviewModel.is_active == True)
    )
    reviews = reviews_result.all()
    return reviews


@router.get("/products/{product_id}/reviews/", response_model=list[ReviewSchema], status_code=status.HTTP_200_OK)
async def get_review(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список активных отзывов для указанного товара.
    """
    # Проверяем, существует ли активный товар
    product = await db.scalar(
        select(ProductModel).where(ProductModel.id == product_id,
                                    ProductModel.is_active == True)
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Product not found or inactive")

    # Получаем активные отзывы товара
    reviews_result = await db.scalars(
        select(ReviewModel).where(ReviewModel.product_id == product_id,
                                   ReviewModel.is_active == True)
    )
    reviews = reviews_result.all()
    return reviews


@router.post("/reviews/", response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def create_post(
    review: ReviewCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_buyer)
):
    """
    Создаёт новый отзыв, привязанный к текущему покупателю (только для 'buyer').
    """
    # Проверяем, существует ли активный товар
    result = await db.scalars(
        select(ProductModel)
        .where(ProductModel.id == review.product_id,
        ProductModel.is_active == True)
    )
    db_product = result.first()
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Проверяем, оставлял ли пользователь отзыв указанному товару
    review_result = await db.scalars(
        select(ReviewModel).where(ReviewModel.product_id == review.product_id, ReviewModel.user_id == current_user.id)
    )
    if review_result.first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already have feedback")

    db_review = ReviewModel(**review.model_dump(), user_id=current_user.id)
    db.add(db_review)

    # Пересчет рейтинга
    result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == review.product_id,
            ReviewModel.is_active == True
        )
    )
    avg_rating = result.scalar() or 0.0
    product = await db.get(ProductModel, review.product_id)
    product.rating = avg_rating

    await db.commit()
    await db.refresh(db_review)  # Для получения id и is_active из базы
    return db_review


@router.delete("/reviews/{review_id}", status_code=status.HTTP_200_OK)
async def delete_review(
        review_id: int,
        db: AsyncSession = Depends(get_async_db),
        _current_user: UserModel = Depends(get_current_admin)
):
    """
    Выполняет мягкое удаление отзыва (только для 'admin').
    """

    # Проверяем, существует ли активный отзыв
    result = await db.scalars(
        select(ReviewModel).where(ReviewModel.id == review_id, ReviewModel.is_active == True)
    )
    review = result.first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found or inactive")

    # Мягкое удаление
    review.is_active = False

    # Пересчет рейтинга
    result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == review.product_id,
            ReviewModel.is_active == True
        )
    )
    avg_rating = result.scalar() or 0.0
    product = await db.get(ProductModel, review.product_id)
    product.rating = avg_rating

    await db.commit()
    await db.refresh(review)  # Для возврата is_active = False
    return {"message": "Review deleted"}