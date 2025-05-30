"""Add title field to Extraction model

Revision ID: fc1f206145d8
Revises: e942f1e31b59
Create Date: 2025-04-23 00:28:03.667900

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fc1f206145d8'
down_revision = 'e942f1e31b59'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('extraction', schema=None) as batch_op:
        batch_op.add_column(sa.Column('title', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('error_message', sa.Text(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('extraction', schema=None) as batch_op:
        batch_op.drop_column('error_message')
        batch_op.drop_column('title')

    # ### end Alembic commands ###
