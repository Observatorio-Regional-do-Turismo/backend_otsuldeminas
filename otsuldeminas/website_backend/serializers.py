from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from .models import Cidade, Contato, Estado, Evento, Imagem, PontoTuristico


class ImagemSerializer(serializers.ModelSerializer):
  class Meta:
    model = Imagem
    fields = ["id", "image", "alt_text", "caption", "order", "is_cover"]


class ContatoSerializer(serializers.ModelSerializer):
  type_display = serializers.CharField(source="get_type_display", read_only=True)
  class Meta:
    model = Contato
    fields = [
      "id",
      "type",
      "type_display",
      "label",
      "value",
      "address",
      "latitude",
      "longitude",
      "order",
    ]


class GenericRelatedSerializerMixin:
  def create(self, validated_data):
    imagens_data = validated_data.pop("imagens", [])
    contatos_data = validated_data.pop("contatos", [])
    instance = super().create(validated_data)
    self._save_related(instance, imagens_data, contatos_data)
    return instance

  def update(self, instance, validated_data):
    imagens_data = validated_data.pop("imagens", None)
    contatos_data = validated_data.pop("contatos", None)
    instance = super().update(instance, validated_data)

    # Nested lists are treated as full replacements when provided.
    if imagens_data is not None:
      instance.image_relations.all().delete()
      self._save_related(instance, imagens_data, [])

    if contatos_data is not None:
      instance.contact_relations.all().delete()
      self._save_related(instance, [], contatos_data)

    return instance

  def _save_related(self, instance, imagens_data, contatos_data):
    content_type = ContentType.objects.get_for_model(instance)
    for data in imagens_data:
      Imagem.objects.create(
        content_type=content_type, object_id=instance.pk, **data
      )
    for data in contatos_data:
      Contato.objects.create(
        content_type=content_type, object_id=instance.pk, **data
      )


class EstadoSerializer(GenericRelatedSerializerMixin, serializers.ModelSerializer):
  imagens = ImagemSerializer(many=True, required=False)
  contatos = ContatoSerializer(many=True, required=False)

  class Meta:
    model = Estado
    fields = [
      "id",
      "name",
      "slug",
      "description",
      "abbreviation",
      "imagens",
      "contatos",
    ]


class CidadeSerializer(GenericRelatedSerializerMixin, serializers.ModelSerializer):
  imagens = ImagemSerializer(many=True, required=False)
  contatos = ContatoSerializer(many=True, required=False)
  state_name = serializers.CharField(source="state.name", read_only=True)

  class Meta:
    model = Cidade
    fields = [
      "id",
      "name",
      "slug",
      "description",
      "state",
      "state_name",
      "ibge_code",
      "hospedagens",
      "restaurantes",
      "populacao",
      "pib",
      "imagens",
      "contatos",
    ]
    read_only_fields = (
      "hospedagens",
      "restaurantes",
      "populacao",
      "pib",
    )


class EventoSerializer(GenericRelatedSerializerMixin, serializers.ModelSerializer):
  imagens = ImagemSerializer(many=True, required=False)
  contatos = ContatoSerializer(many=True, required=False)
  cidade_name = serializers.CharField(source="cidade.name", read_only=True)

  class Meta:
    model = Evento
    fields = [
      "id",
      "name",
      "slug",
      "description",
      "cidade",
      "cidade_name",
      "start_date",
      "end_date",
      "imagens",
      "contatos",
    ]

  def validate(self, attrs):
    start_date = attrs.get(
      "start_date", getattr(self.instance, "start_date", None)
    )
    end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
    if end_date and start_date and end_date < start_date:
      raise serializers.ValidationError(
        {"end_date": "end_date must be greater than or equal to start_date."}
      )
    return attrs


class PontoTuristicoSerializer(
  GenericRelatedSerializerMixin, serializers.ModelSerializer
):
  imagens = ImagemSerializer(many=True, required=False)
  contatos = ContatoSerializer(many=True, required=False)
  cidade_name = serializers.CharField(source="cidade.name", read_only=True)

  class Meta:
    model = PontoTuristico
    fields = [
      "id",
      "name",
      "slug",
      "description",
      "cidade",
      "cidade_name",
      "imagens",
      "contatos",
    ]
