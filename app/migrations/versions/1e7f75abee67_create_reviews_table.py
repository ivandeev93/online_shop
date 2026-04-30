from alembic import op
import sqlalchemy as sa

revision = 'create_reviews_table'
down_revision = '46415d8918d7'  # последняя миграция
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('comment_date', sa.DateTime(), nullable=False),
        sa.Column('grade', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade():
    op.drop_table('reviews')
