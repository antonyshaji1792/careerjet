import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models.subscription import Plan

@click.command('seed-plans')
@with_appcontext
def seed_plans_command():
    """Seed initial subscription plans."""
    plans_to_seed = [
        {
            'name': 'CareerJet Starter',
            'monthly_price': 499,
            'monthly_credits': 300,
        },
        {
            'name': 'CareerJet Pro',
            'monthly_price': 999,
            'monthly_credits': 800,
        },
        {
            'name': 'CareerJet Elite',
            'monthly_price': 1999,
            'monthly_credits': 2000,
        }
    ]

    for plan_data in plans_to_seed:
        # Idempotent check by name
        existing_plan = Plan.query.filter_by(name=plan_data['name']).first()
        if existing_plan:
            click.echo(f"Plan '{plan_data['name']}' already exists. Updating...")
            existing_plan.monthly_price = plan_data['monthly_price']
            existing_plan.monthly_credits = plan_data['monthly_credits']
            existing_plan.is_active = True
        else:
            click.echo(f"Creating plan '{plan_data['name']}'...")
            new_plan = Plan(
                name=plan_data['name'],
                monthly_price=plan_data['monthly_price'],
                monthly_credits=plan_data['monthly_credits'],
                razorpay_plan_id=None,
                is_active=True
            )
            db.session.add(new_plan)
    
    db.session.commit()
    click.echo("Seeding completed successfully!")

def register_commands(app):
    app.cli.add_command(seed_plans_command)
