import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clickify", "0002_clicklog_ref_alter_trackedlink_target_url"),
    ]

    operations = [
        migrations.CreateModel(
            name="UtmSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.CharField(
                    max_length=255, unique=True,
                    help_text=(
                        "The utm_source value sent to analytics. "
                        "e.g. 'email', 'google', 'facebook', 'newsletter'. "
                        "Use lowercase with no spaces — this is what appears in your reports."
                    ),
                )),
                ("label", models.CharField(
                    max_length=255, blank=True,
                    help_text=(
                        "Optional human-readable description shown in the admin dropdown. "
                        "e.g. 'Email Newsletter', 'Google Ads'. Leave blank to use the value."
                    ),
                )),
            ],
            options={"ordering": ["value"]},
        ),
        migrations.CreateModel(
            name="UtmMedium",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.CharField(
                    max_length=255, unique=True,
                    help_text=(
                        "The utm_medium value sent to analytics. "
                        "e.g. 'email', 'cpc', 'social', 'organic', 'referral'. "
                        "Use lowercase with no spaces — this is what appears in your reports."
                    ),
                )),
                ("label", models.CharField(
                    max_length=255, blank=True,
                    help_text=(
                        "Optional human-readable description shown in the admin dropdown. "
                        "e.g. 'Email Campaign', 'Paid Search'. Leave blank to use the value."
                    ),
                )),
            ],
            options={"ordering": ["value"]},
        ),
        migrations.AddField(
            model_name="trackedlink",
            name="utm_source",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tracked_links",
                to="clickify.utmsource",
                help_text=(
                    "Identifies the traffic origin for this link. "
                    "e.g. 'email' for a newsletter, 'google' for a Google Ad. "
                    "Manage available options in the UTM Sources section."
                ),
            ),
        ),
        migrations.AddField(
            model_name="trackedlink",
            name="utm_medium",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tracked_links",
                to="clickify.utmmedium",
                help_text=(
                    "Identifies the marketing channel type for this link. "
                    "e.g. 'email' for email campaigns, 'cpc' for paid search. "
                    "Manage available options in the UTM Mediums section."
                ),
            ),
        ),
        migrations.AddField(
            model_name="trackedlink",
            name="utm_campaign",
            field=models.CharField(
                max_length=255, blank=True,
                help_text=(
                    "The specific campaign this link belongs to. "
                    "e.g. 'q3-newsletter-2026', 'spring-sale', 'product-launch'. "
                    "Use lowercase with hyphens — no spaces. Leave blank if not part of a campaign."
                ),
            ),
        ),
        migrations.AddField(
            model_name="trackedlink",
            name="utm_content",
            field=models.CharField(
                max_length=255, blank=True,
                help_text=(
                    "Identifies this specific link within a campaign. "
                    "e.g. 'header-cta', 'footer-button', 'sidebar-image'. "
                    "Use this to distinguish multiple links in the same email or page."
                ),
            ),
        ),
        migrations.AddField(
            model_name="trackedlink",
            name="utm_term",
            field=models.CharField(
                max_length=255, blank=True,
                help_text=(
                    "The paid search keyword that triggered this ad. "
                    "e.g. 'running+shoes'. Leave blank for non-paid-search links."
                ),
            ),
        ),
        migrations.AddField(
            model_name="trackedlink",
            name="utm_override",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Controls what happens when a visitor arrives with UTM parameters already "
                    "in their click URL (e.g. from a social share or forwarded link). "
                    "Checked: this link's stored UTM values always win — incoming params are replaced. "
                    "Unchecked: incoming params take precedence; stored values fill any gaps."
                ),
            ),
        ),
        migrations.AddField(
            model_name="trackedlink",
            name="forward_params",
            field=models.CharField(
                max_length=1024, blank=True,
                help_text=(
                    "Comma-separated list of non-UTM query parameter names to forward from "
                    "the visitor's click URL to the destination. "
                    "e.g. 'name, ref_id, campaign_token'. "
                    "UTM parameters are always handled separately via the UTM fields above. "
                    "Leave blank to forward no extra parameters (recommended for public links)."
                ),
            ),
        ),
        migrations.AddField(
            model_name="clicklog",
            name="utm_source",
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="clicklog",
            name="utm_medium",
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="clicklog",
            name="utm_campaign",
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="clicklog",
            name="utm_content",
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="clicklog",
            name="utm_term",
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
    ]
