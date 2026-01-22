# Generated migration for multiple choice questions

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_quizgenre_pubquizsession_genrevote_quizquestion_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='quizquestion',
            name='question_type',
            field=models.CharField(
                choices=[
                    ('multiple_choice', 'Multiple Choice'),
                    ('written', 'Written Answer'),
                    ('picture', 'Picture Round'),
                    ('music', 'Music/Audio'),
                    ('buzzer', 'Buzzer Question'),
                    ('bonus', 'Bonus'),
                ],
                default='multiple_choice',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='quizquestion',
            name='options',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="For multiple choice: {'A': 'Paris', 'B': 'London', 'C': 'Berlin', 'D': 'Madrid'}"
            ),
        ),
        migrations.AddField(
            model_name='quizquestion',
            name='correct_option',
            field=models.CharField(
                blank=True,
                help_text='For multiple choice: A, B, C, or D',
                max_length=1
            ),
        ),
    ]
