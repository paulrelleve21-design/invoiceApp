from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0004_invoice_business_address_invoice_business_email_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='template_choice',
            field=models.CharField(default='1', max_length=32),
        ),
    ]
