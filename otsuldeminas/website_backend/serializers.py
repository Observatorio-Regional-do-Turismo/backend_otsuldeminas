from rest_framework import serializers
from .manager_serializers import clean_rich_text
from .models import Cidade, CidadeData, Contato, Estado, Evento, Imagem, Noticia, PontoTuristico, IGR


# IMAGENS ==============================================================================================================
class ImagemSerializer(serializers.ModelSerializer):
  class Meta:
    model = Imagem
    fields = [field.name for field in Imagem._meta.fields]


# CONTATOS =============================================================================================================
class ContatoSerializer(serializers.ModelSerializer):
  type_display = serializers.CharField(source="get_type_display", read_only=True)
  
  class Meta:
    model = Contato
    fields = [field.name for field in Contato._meta.fields] + ["type_display"]


# ESTADOS ==============================================================================================================
class EstadoSerializer(serializers.ModelSerializer):
  imagens = ImagemSerializer(many=True, required=False)
  contatos = ContatoSerializer(many=True, required=False)

  class Meta:
    model = Estado
    fields = [field.name for field in Estado._meta.fields] + ["imagens", "contatos"]


# IGRs ==============================================================================================================
class IGRSerializer(serializers.ModelSerializer):
  imagens = ImagemSerializer(many=True, required=False)
  contatos = ContatoSerializer(many=True, required=False)
  description = serializers.SerializerMethodField()

  class Meta:
    model = IGR
    fields = [field.name for field in IGR._meta.fields] + ["imagens", "contatos"]

  def get_description(self, obj):
    return clean_rich_text(obj.description)


# CIDADES ==============================================================================================================
class CidadeDataSerializer(serializers.ModelSerializer):
  class Meta:
    model = CidadeData
    fields = [field.name for field in CidadeData._meta.fields if field.name != "cidade"]


class CidadeSerializer(serializers.ModelSerializer):
  imagens = ImagemSerializer(many=True, required=False)
  contatos = ContatoSerializer(many=True, required=False)
  description = serializers.SerializerMethodField()

  class Meta:
    model = Cidade
    fields = [field.name for field in Cidade._meta.fields] + ["contatos", "imagens"]
    read_only_fields = ()

  def get_description(self, obj):
    return clean_rich_text(obj.description)


class CidadeDetailSerializer(CidadeSerializer):
  information = CidadeDataSerializer(read_only=True)

  class Meta(CidadeSerializer.Meta):
    fields = CidadeSerializer.Meta.fields + ["information"]


# EVENTOS ==============================================================================================================
class EventoSerializer(serializers.ModelSerializer):
  imagens = ImagemSerializer(many=True, required=False)
  contatos = ContatoSerializer(many=True, required=False)
  cidade_name = serializers.CharField(source="cidade.name", read_only=True)
  cidade_slug = serializers.CharField(source="cidade.slug", read_only=True)

  class Meta:
    model = Evento
    fields = [field.name for field in Evento._meta.fields] + [
      "cidade_name", "cidade_slug", "imagens", "contatos"
    ]

  def validate(self, attrs):
    start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
    end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
    if end_date and start_date and end_date < start_date:
      raise serializers.ValidationError({"end_date": "end_date must be greater than or equal to start_date."})
    return attrs


# PONTOS TURÍSTICOS ====================================================================================================
class PontoTuristicoSerializer(serializers.ModelSerializer):
  imagens = ImagemSerializer(many=True, required=False)
  contatos = ContatoSerializer(many=True, required=False)

  class Meta:
    model = PontoTuristico
    fields = [field.name for field in PontoTuristico._meta.fields] + ["imagens", "contatos"]


# NOTÍCIAS =============================================================================================================
class NoticiaSerializer(serializers.ModelSerializer):
  imagens = ImagemSerializer(many=True, read_only=True)
  cidade_name = serializers.CharField(source="cidade.name", read_only=True, allow_null=True)
  cidade_slug = serializers.CharField(source="cidade.slug", read_only=True, allow_null=True)
  igr_name = serializers.CharField(source="igr.name", read_only=True, allow_null=True)
  igr_slug = serializers.CharField(source="igr.slug", read_only=True, allow_null=True)
  image = serializers.SerializerMethodField()
  content = serializers.SerializerMethodField()

  class Meta:
    model = Noticia
    fields = [
      "id", "title", "slug", "summary", "content", "published_at", "is_featured",
      "cidade", "cidade_name", "cidade_slug", "igr", "igr_name", "igr_slug",
      "category", "author", "image", "imagens", "tags", "source_url",
    ]

  def get_image(self, obj):
    image = obj.imagens.filter(is_cover=True).first() or obj.imagens.first()
    if image is None:
      return None
    request = self.context.get("request")
    return request.build_absolute_uri(image.image.url) if request else image.image.url

  def get_content(self, obj):
    return clean_rich_text(obj.content)
