# Generated by Django 5.2.1 on 2025-05-22 10:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ad',
            name='category',
            field=models.CharField(choices=[('books', 'Книги'), ('electronics', 'Электроника'), ('clothing', 'Одежда'), ('furniture', 'Мебель'), ('sports', 'Спорт'), ('other', 'Другое')], max_length=100, verbose_name='Категория'),
        ),
    ]
