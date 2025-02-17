"""added agent_id to ticket

Revision ID: bf6b60da26df
Revises: 
Create Date: 2025-02-03 21:13:51.119758

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bf6b60da26df'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('ticket', schema=None) as batch_op:
        batch_op.add_column(sa.Column('agent_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, 'user', ['agent_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('ticket', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('agent_id')

    # ### end Alembic commands ###
