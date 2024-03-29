"""Edit staff_allowed_faculty service

Revision ID: 992e3782a12e
Revises: 55406f6f1309
Create Date: 2024-03-19 12:18:19.091995

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '992e3782a12e'
down_revision = '55406f6f1309'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('staff_allowed_faculty', sa.Column('short_name', sa.String(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('staff_allowed_faculty', 'short_name')
    # ### end Alembic commands ###
