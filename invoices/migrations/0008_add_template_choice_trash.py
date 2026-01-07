from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0007_merge_20260107_1751'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoicetrash',
            name='template_choice',
            field=models.CharField(default='1', max_length=2),
        ),
    ]
