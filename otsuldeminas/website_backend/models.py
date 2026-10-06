from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django_ckeditor_5.fields import CKEditor5Field


# INFORMAÇÕES BASICAS ==================================================================================================
class InformacaoBasica(models.Model):
  name = models.CharField(max_length=255)
  slug = models.SlugField(max_length=255)
  description = CKEditor5Field(config_name="default", blank=True)

  class Meta:
    abstract = True

  def __str__(self):
    return self.name


# IMAGENS ==============================================================================================================
class Imagem(models.Model):
  image = models.ImageField(upload_to="website/images/")
  alt_text = models.CharField(max_length=255, null=True, blank=True, help_text="Texto alternativo para acessibilidade e SEO.",)
  caption = models.CharField(max_length=255, null=True, blank=True)
  order = models.PositiveIntegerField(default=0)
  is_cover = models.BooleanField(default=False)

  content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
  object_id = models.PositiveBigIntegerField()
  content_object = GenericForeignKey("content_type", "object_id")

  class Meta:
    ordering = ["order", "id"]
    indexes = [models.Index(fields=["content_type", "object_id"])]

  def __str__(self):
    return self.image.name


# CONTATOS =============================================================================================================
class Contato(models.Model):
  class Tipo(models.TextChoices):
    WEBSITE = "website", "Site"
    EMAIL = "email", "E-mail"
    PHONE = "phone", "Telefone"
    WHATSAPP = "whatsapp", "WhatsApp"
    INSTAGRAM = "instagram", "Instagram"
    FACEBOOK = "facebook", "Facebook"
    YOUTUBE = "youtube", "YouTube"
    TIKTOK = "tiktok", "TikTok"
    LOCATION = "location", "Localização"

  object_id = models.PositiveBigIntegerField()
  content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
  content_object = GenericForeignKey("content_type", "object_id")

  type = models.CharField(max_length=30, choices=Tipo.choices)
  label = models.CharField(max_length=255)
  value = models.TextField(max_length=500)
  order = models.PositiveIntegerField(default=0)

  latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])
  longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])

  class Meta:
    ordering = ["order", "id"]
    indexes = [models.Index(fields=["content_type", "object_id"])]

  def __str__(self):
    return f"{self.get_type_display()}: {self.value or self.address}"


# ESTADOS ==============================================================================================================
class Estado(InformacaoBasica):
  id = models.BigAutoField(primary_key=True)
  abbreviation = models.CharField(max_length=2, unique=True)
  
  image_relations = GenericRelation(Imagem, related_query_name="estado")
  contact_relations = GenericRelation(Contato, related_query_name="estado")

  class Meta:
    verbose_name = "Estado"
    verbose_name_plural = "Estados"
    ordering = ["name"]

  def __str__(self):
    return self.name

  @property
  def imagens(self):
    return self.image_relations.all()

  @property
  def contatos(self):
    return self.contact_relations.all()


# IGRs ==============================================================================================================
class IGR(InformacaoBasica):
  id = models.BigAutoField(primary_key=True)
  
  image_relations = GenericRelation(Imagem, related_query_name="estado")
  contact_relations = GenericRelation(Contato, related_query_name="estado")
  
  class Meta:
    verbose_name = "IGR"
    verbose_name_plural = "IGRs"
    ordering = ["name"]

  def __str__(self):
    return self.name
  
  @property
  def imagens(self):
    return self.image_relations.all()
  
  @property
  def contatos(self):
    return self.contact_relations.all()


# CIDADES ==============================================================================================================
class Cidade(InformacaoBasica):
  id = models.BigAutoField(primary_key=True)

  ibge_code = models.CharField(max_length=7, unique=True, null=True, blank=True)
  latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])
  longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])

  state = models.ForeignKey(Estado, on_delete=models.CASCADE, related_name="cidades")
  igr = models.ForeignKey(IGR, on_delete=models.SET_NULL, null=True, blank=True, related_name="cidades")
  image_relations = GenericRelation(Imagem, related_query_name="cidade")
  contact_relations = GenericRelation(Contato, related_query_name="cidade")

  class Meta:
    verbose_name = "Cidade"
    verbose_name_plural = "Cidades"
    ordering = ["name"]
    constraints = [
      models.UniqueConstraint(fields=["state", "slug"], name="unique_cidade_slug_por_estado",),
    ]

  def __str__(self):
    return self.name

  @property
  def imagens(self):
    return self.image_relations.all()

  @property
  def contatos(self):
    return self.contact_relations.all()


class CidadeData(models.Model):
  id = models.BigAutoField(primary_key=True)
  
  populacao = models.PositiveIntegerField(null=True)
  pib = models.PositiveIntegerField(null=True)
  pib_per_capta = models.PositiveIntegerField(null=True)
  idh = models.FloatField(null=True)
  idhm = models.FloatField(null=True)
  hospedagens = models.PositiveIntegerField(null=True)
  leitos = models.PositiveIntegerField(null=True)
  restaurantes = models.PositiveIntegerField(null=True)
  munic = models.PositiveIntegerField(null=True)
  indicador_cultural_munic = models.PositiveIntegerField(null=True)
  munic_cultura = models.PositiveIntegerField(null=True)
  pnad = models.PositiveIntegerField(null=True)
  estatistica_pnad = models.PositiveIntegerField(null=True)
  pnad_rendimento = models.PositiveIntegerField(null=True)
  pnad_ocupacao = models.PositiveIntegerField(null=True)
  area_territorial = models.FloatField(null=True)
  area = models.FloatField(null=True)
  densidade_demografica = models.FloatField(null=True)
  densidade = models.FloatField(null=True)
  escolarizacao = models.FloatField(null=True)
  taxa_escolarizacao = models.FloatField(null=True)

  cidade = models.OneToOneField(Cidade, on_delete=models.CASCADE, related_name="information")


# EVENTOS ==============================================================================================================
class Evento(InformacaoBasica):
  id = models.BigAutoField(primary_key=True)
  start_date = models.DateTimeField()
  end_date = models.DateTimeField(null=True, blank=True)

  cidade = models.ForeignKey(Cidade, on_delete=models.CASCADE, related_name="eventos",)
  image_relations = GenericRelation(Imagem, related_query_name="evento")
  contact_relations = GenericRelation(Contato, related_query_name="evento")

  class Meta:
    verbose_name = "Evento"
    verbose_name_plural = "Eventos"
    ordering = ["start_date"]
    constraints = [
      models.UniqueConstraint(fields=["cidade", "slug"], name="unique_evento_slug_por_cidade"),
      models.CheckConstraint(condition=(models.Q(end_date__isnull=True) | models.Q(end_date__gte=models.F("start_date"))), name="evento_end_date_maior_ou_igual_start_date"),
    ]

  def __str__(self):
    return self.name

  @property
  def imagens(self):
    return self.image_relations.all()

  @property
  def contatos(self):
    return self.contact_relations.all()


# PONTOS TURÍSTICOS ====================================================================================================
class PontoTuristico(InformacaoBasica):
  id = models.BigAutoField(primary_key=True)
  
  cidade = models.ForeignKey(Cidade, on_delete=models.CASCADE, related_name="pontos_turisticos")
  image_relations = GenericRelation(Imagem, related_query_name="ponto_turistico")
  contact_relations = GenericRelation(Contato, related_query_name="ponto_turistico")
  
  class Meta:
    verbose_name = "Ponto Turístico"
    verbose_name_plural = "Pontos Turísticos"
    ordering = ["name"]
    constraints = [
      models.UniqueConstraint(fields=["cidade", "slug"], name="unique_ponto_slug_por_cidade",),
    ]

  def __str__(self):
    return self.name

  @property
  def imagens(self):
    return self.image_relations.all()

  @property
  def contatos(self):
    return self.contact_relations.all()


# GESTOR CIDADE =============================================================================================================
class GestorCidade(models.Model):
  user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="gestor_cidade")
  
  cidade = models.ForeignKey(Cidade, on_delete=models.CASCADE, related_name="gestores")

  class Meta:
    verbose_name = "Gestor de Cidade"
    verbose_name_plural = "Gestores de Cidade"

  def __str__(self):
    return f"{self.user} → {self.cidade}"


# GESTOR IGR =============================================================================================================
class GestorIGR(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="gestor_igr")
	
	igr = models.ForeignKey(IGR, on_delete=models.CASCADE, related_name="gestores")
	
	class Meta:
		verbose_name = "Gestor de IGR"
		verbose_name_plural = "Gestores de IGR"
	
	def __str__(self):
		return f"{self.user} → {self.igr}"
