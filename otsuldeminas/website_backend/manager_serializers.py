import bleach
from rest_framework import serializers

from .manager_auth import get_manager_scopes
from .models import Cidade, IGR, Noticia


RICH_TEXT_TAGS = {
  "a", "blockquote", "br", "h2", "h3", "h4", "hr", "li", "ol", "p",
  "strong", "em", "u", "ul", "table", "thead", "tbody", "tr", "th", "td",
}


def clean_rich_text(value):
  return bleach.clean(
    value,
    tags=RICH_TEXT_TAGS,
    attributes={"a": ["href", "title", "target", "rel"]},
    protocols={"http", "https", "mailto"},
    strip=True,
    strip_comments=True,
  )


class ManagerCitySerializer(serializers.ModelSerializer):
  description = serializers.CharField(required=False, allow_blank=True)
  state_name = serializers.CharField(source="state.name", read_only=True)

  class Meta:
    model = Cidade
    fields = ["id", "name", "slug", "description", "state", "state_name"]
    read_only_fields = ["id", "state", "state_name"]

  def to_representation(self, instance):
    data = super().to_representation(instance)
    data["description"] = clean_rich_text(data["description"])
    return data

  def validate_description(self, value):
    return clean_rich_text(value)


class ManagerIGRSerializer(serializers.ModelSerializer):
  description = serializers.CharField(required=False, allow_blank=True)

  class Meta:
    model = IGR
    fields = ["id", "name", "slug", "description"]
    read_only_fields = ["id"]

  def to_representation(self, instance):
    data = super().to_representation(instance)
    data["description"] = clean_rich_text(data["description"])
    return data

  def validate_description(self, value):
    return clean_rich_text(value)


class ManagerNoticiaSerializer(serializers.ModelSerializer):
  content = serializers.CharField(required=False, allow_blank=True)
  summary = serializers.CharField(required=False, allow_blank=True)
  tags = serializers.ListField(
    child=serializers.CharField(max_length=50),
    required=False,
    allow_empty=True,
  )

  class Meta:
    model = Noticia
    fields = [
      "id", "title", "slug", "summary", "content", "published_at",
      "is_featured", "cidade", "igr", "category", "author", "source_url", "tags",
    ]
    read_only_fields = ["id"]

  def to_representation(self, instance):
    data = super().to_representation(instance)
    data["content"] = clean_rich_text(data["content"])
    return data

  def validate_content(self, value):
    return clean_rich_text(value)

  def validate(self, attrs):
    current_city, current_igr = get_manager_scopes(self.context["request"].user)
    city = attrs.get("cidade", getattr(self.instance, "cidade", None))
    igr = attrs.get("igr", getattr(self.instance, "igr", None))

    if self.instance is None:
      if city is None and current_city is not None:
        city = current_city
      if igr is None and city is not None:
        igr = city.igr
      if igr is None and current_igr is not None:
        igr = current_igr

    city_is_in_scope = (
      city is None
      or city == current_city
      or (current_igr is not None and city.igr_id == current_igr.pk)
    )
    igr_is_in_scope = (
      igr is None
      or igr == current_igr
      or (current_city is not None and current_city.igr_id == igr.pk)
    )

    if not city_is_in_scope:
      raise serializers.ValidationError({"cidade": "Você não pode associar notícias a esta cidade."})
    if not igr_is_in_scope:
      raise serializers.ValidationError({"igr": "Você não pode associar notícias a esta IGR."})
    if city is None and igr is None:
      raise serializers.ValidationError("A notícia deve estar vinculada à sua cidade ou IGR.")

    attrs["cidade"] = city
    attrs["igr"] = igr
    return attrs
