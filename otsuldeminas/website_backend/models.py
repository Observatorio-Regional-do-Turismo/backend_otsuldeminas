from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


class InformacaoBasica(models.Model):
  name = models.CharField(max_length=255)
  slug = models.SlugField(max_length=255)
  description = models.TextField(blank=True)

  class Meta:
    abstract = True

  def __str__(self):
    return self.name


class Imagem(models.Model):
  image = models.ImageField(upload_to="website/images/")
  alt_text = models.CharField(max_length=255, blank=True, help_text="Texto alternativo para acessibilidade e SEO.",)
  caption = models.CharField(max_length=255, blank=True)
  order = models.PositiveIntegerField(default=0)
  is_cover = models.BooleanField(default=False)

  content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
  object_id = models.PositiveBigIntegerField()
  content_object = GenericForeignKey("content_type", "object_id")

  class Meta:
    ordering = ["order", "id"]
    indexes = [
      models.Index(fields=["content_type", "object_id"]),
    ]

  def __str__(self):
    return self.image.name


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
    ADDRESS = "address", "Endereço"
    LOCATION = "location", "Localização"

  content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
  object_id = models.PositiveBigIntegerField()
  content_object = GenericForeignKey("content_type", "object_id")

  type = models.CharField(max_length=30, choices=Tipo.choices)
  label = models.CharField(max_length=255, blank=True)
  value = models.TextField(blank=True)

  address = models.CharField(max_length=500, blank=True)
  latitude = models.DecimalField(
    max_digits=9,
    decimal_places=6,
    null=True,
    blank=True,
    validators=[
      MinValueValidator(-90),
      MaxValueValidator(90),
    ],
  )
  longitude = models.DecimalField(
    max_digits=9,
    decimal_places=6,
    null=True,
    blank=True,
    validators=[
      MinValueValidator(-180),
      MaxValueValidator(180),
    ],
  )

  order = models.PositiveIntegerField(default=0)

  class Meta:
    ordering = ["order", "id"]
    indexes = [
      models.Index(fields=["content_type", "object_id"]),
    ]

  def __str__(self):
    return f"{self.get_type_display()}: {self.value or self.address}"


class Estado(InformacaoBasica):
  id = models.BigAutoField(primary_key=True)

  abbreviation = models.CharField(max_length=2, unique=True)
  image_relations = GenericRelation(
    Imagem,
    related_query_name="estado",
  )
  contact_relations = GenericRelation(
    Contato,
    related_query_name="estado",
  )

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


class Cidade(InformacaoBasica):
  id = models.BigAutoField(primary_key=True)

  state = models.ForeignKey(
    Estado,
    on_delete=models.CASCADE,
    related_name="cidades",
  )

  ibge_code = models.CharField(
    max_length=7,
    unique=True,
    null=True,
    blank=True,
  )

  hospedagens = models.PositiveIntegerField(default=0)
  restaurantes = models.PositiveIntegerField(default=0)
  populacao = models.PositiveIntegerField(default=0)
  pib = models.PositiveIntegerField(default=0)

  image_relations = GenericRelation(
    Imagem,
    related_query_name="cidade",
  )
  contact_relations = GenericRelation(
    Contato,
    related_query_name="cidade",
  )

  class Meta:
    verbose_name = "Cidade"
    verbose_name_plural = "Cidades"
    ordering = ["name"]
    constraints = [
      models.UniqueConstraint(
        fields=["state", "slug"],
        name="unique_cidade_slug_por_estado",
      ),
    ]

  def __str__(self):
    return self.name

  @property
  def imagens(self):
    return self.image_relations.all()

  @property
  def contatos(self):
    return self.contact_relations.all()


class Evento(InformacaoBasica):
  id = models.BigAutoField(primary_key=True)

  cidade = models.ForeignKey(
    Cidade,
    on_delete=models.CASCADE,
    related_name="eventos",
  )

  start_date = models.DateTimeField()
  end_date = models.DateTimeField(null=True, blank=True)

  image_relations = GenericRelation(
    Imagem,
    related_query_name="evento",
  )
  contact_relations = GenericRelation(
    Contato,
    related_query_name="evento",
  )

  class Meta:
    verbose_name = "Evento"
    verbose_name_plural = "Eventos"
    ordering = ["start_date"]
    constraints = [
      models.UniqueConstraint(
        fields=["cidade", "slug"],
        name="unique_evento_slug_por_cidade",
      ),
      models.CheckConstraint(
        condition=(
                models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date"))
        ),
        name="evento_end_date_maior_ou_igual_start_date",
      ),
    ]

  def __str__(self):
    return self.name

  @property
  def imagens(self):
    return self.image_relations.all()

  @property
  def contatos(self):
    return self.contact_relations.all()


class PontoTuristico(InformacaoBasica):
  id = models.BigAutoField(primary_key=True)

  cidade = models.ForeignKey(
    Cidade,
    on_delete=models.CASCADE,
    related_name="pontos_turisticos",
  )

  image_relations = GenericRelation(
    Imagem,
    related_query_name="ponto_turistico",
  )
  contact_relations = GenericRelation(
    Contato,
    related_query_name="ponto_turistico",
  )

  class Meta:
    verbose_name = "Ponto Turístico"
    verbose_name_plural = "Pontos Turísticos"
    ordering = ["name"]
    constraints = [
      models.UniqueConstraint(
        fields=["cidade", "slug"],
        name="unique_ponto_slug_por_cidade",
      ),
    ]

  def __str__(self):
    return self.name

  @property
  def imagens(self):
    return self.image_relations.all()

  @property
  def contatos(self):
    return self.contact_relations.all()


class GestorCidade(models.Model):
  user = models.OneToOneField(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name="gestor_cidade",
  )
  cidade = models.ForeignKey(
    "Cidade",
    on_delete=models.CASCADE,
    related_name="gestores",
  )

  class Meta:
    verbose_name = "Gestor de Cidade"
    verbose_name_plural = "Gestores de Cidade"

  def __str__(self):
    return f"{self.user} → {self.cidade}"
