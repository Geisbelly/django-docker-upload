from django.db import migrations, models

import core.models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Documento",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("titulo", models.CharField(max_length=200, verbose_name="titulo")),
                (
                    "arquivo",
                    models.FileField(
                        upload_to=core.models.upload_to, verbose_name="arquivo"
                    ),
                ),
                (
                    "enviado_em",
                    models.DateTimeField(auto_now_add=True, verbose_name="enviado em"),
                ),
            ],
            options={
                "verbose_name": "documento",
                "verbose_name_plural": "documentos",
                "ordering": ["-enviado_em"],
            },
        ),
    ]
