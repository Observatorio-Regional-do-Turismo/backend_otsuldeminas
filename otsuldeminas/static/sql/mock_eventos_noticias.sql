-- Dados de demonstração opcionais para desenvolvimento.
-- Pré-requisitos:
--   1. Aplicar as migrations do website_backend, incluindo 0014_noticia.
--   2. Ter cidades cadastradas com os slugs usados abaixo.
--   3. IGRs de demonstração são criadas e associadas às cidades por este script.
-- Este script é idempotente: pode ser executado novamente sem duplicar registros.
-- Não cria arquivos de imagem; os registros funcionam sem imagens.

BEGIN;

DO $$
BEGIN
  IF EXISTS (
    SELECT required.slug
    FROM (VALUES
      ('pocos-de-caldas'),
      ('caxambu'),
      ('camanducaia'),
      ('sao-lourenco'),
      ('andradas')
    ) AS required(slug)
    WHERE NOT EXISTS (
      SELECT 1
      FROM website_backend_cidade cidade
      WHERE cidade.slug = required.slug
    )
  ) THEN
    RAISE EXCEPTION
      'Mock data was not inserted: run the city seed first (missing one or more expected city slugs).';
  END IF;
END
$$;

INSERT INTO website_backend_igr (name, slug, description)
SELECT seed.name, seed.slug, seed.description
FROM (VALUES
  (
    'IGR Circuito Caminhos Gerais',
    'mock-circuito-caminhos-gerais',
    '<p>IGR fictícia para testar a associação de notícias à governança regional.</p>'
  ),
  (
    'IGR Circuito das Águas de Minas',
    'mock-circuito-das-aguas',
    '<p>IGR fictícia para testar a associação de notícias à governança regional.</p>'
  ),
  (
    'IGR Circuito Serras Verdes',
    'mock-circuito-serras-verdes',
    '<p>IGR fictícia para testar a associação de notícias à governança regional.</p>'
  )
) AS seed(name, slug, description)
WHERE NOT EXISTS (
  SELECT 1
  FROM website_backend_igr existing
  WHERE existing.slug = seed.slug
);

UPDATE website_backend_cidade cidade
SET igr_id = igr.id
FROM (VALUES
  ('pocos-de-caldas', 'mock-circuito-caminhos-gerais'),
  ('andradas', 'mock-circuito-caminhos-gerais'),
  ('caxambu', 'mock-circuito-das-aguas'),
  ('sao-lourenco', 'mock-circuito-das-aguas'),
  ('camanducaia', 'mock-circuito-serras-verdes')
) AS mapping(cidade_slug, igr_slug)
JOIN website_backend_igr igr ON igr.slug = mapping.igr_slug
WHERE cidade.slug = mapping.cidade_slug;

INSERT INTO website_backend_evento
  (name, slug, description, start_date, end_date, cidade_id)
SELECT
  seed.name,
  seed.slug,
  seed.description,
  seed.start_date,
  seed.end_date,
  cidade.id
FROM (VALUES
  (
    'Festival de Inverno de Poços de Caldas',
    'mock-festival-inverno-pocos-2026',
    '<p>Programação demonstrativa com música, gastronomia e atividades culturais no centro da cidade.</p>',
    CURRENT_TIMESTAMP + INTERVAL '14 days',
    CURRENT_TIMESTAMP + INTERVAL '16 days',
    'pocos-de-caldas'
  ),
  (
    'Encontro de Águas e Cultura de Caxambu',
    'mock-encontro-aguas-caxambu-2026',
    '<p>Evento demonstrativo dedicado às águas minerais, ao patrimônio e à cultura local.</p>',
    CURRENT_TIMESTAMP + INTERVAL '30 days',
    CURRENT_TIMESTAMP + INTERVAL '31 days',
    'caxambu'
  ),
  (
    'Mostra de Turismo e Natureza de Camanducaia',
    'mock-mostra-turismo-camanducaia-2026',
    '<p>Feira fictícia com experiências de ecoturismo, trilhas e produtos da região.</p>',
    CURRENT_TIMESTAMP + INTERVAL '45 days',
    CURRENT_TIMESTAMP + INTERVAL '46 days',
    'camanducaia'
  ),
  (
    'Festival Gastronômico de São Lourenço',
    'mock-festival-gastronomico-sao-lourenco-2026',
    '<p>Programação demonstrativa de culinária mineira, produtores locais e música ao vivo.</p>',
    CURRENT_TIMESTAMP + INTERVAL '60 days',
    CURRENT_TIMESTAMP + INTERVAL '62 days',
    'sao-lourenco'
  ),
  (
    'Feira de Vinhos e Sabores de Andradas',
    'mock-feira-vinhos-andradas-2026',
    '<p>Evento fictício para testar filtros de município e período na agenda regional.</p>',
    CURRENT_TIMESTAMP - INTERVAL '30 days',
    CURRENT_TIMESTAMP - INTERVAL '29 days',
    'andradas'
  )
) AS seed(name, slug, description, start_date, end_date, cidade_slug)
JOIN website_backend_cidade cidade ON cidade.slug = seed.cidade_slug
ON CONFLICT (cidade_id, slug) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  start_date = EXCLUDED.start_date,
  end_date = EXCLUDED.end_date;

INSERT INTO website_backend_noticia
  (title, slug, summary, content, published_at, is_featured, category, author, source_url, tags, cidade_id, igr_id)
SELECT
  seed.title,
  seed.slug,
  seed.summary,
  seed.content,
  seed.published_at,
  seed.is_featured,
  seed.category,
  seed.author,
  seed.source_url,
  seed.tags,
  cidade.id,
  COALESCE(igr.id, cidade.igr_id)
FROM (VALUES
  (
    'Poços de Caldas recebe festival regional de turismo e cultura',
    'mock-noticia-festival-turismo-pocos-2026',
    'A cidade prepara uma programação demonstrativa que reúne cultura, gastronomia e experiências turísticas.',
    '<p>Esta notícia fictícia serve para testar a página de notícias e o carrossel de destaques. O festival reúne apresentações culturais, culinária regional e atividades para visitantes.</p>',
    CURRENT_TIMESTAMP - INTERVAL '1 day',
    TRUE,
    'Eventos',
    'Redação de demonstração',
    '',
    '["demonstração", "turismo", "Poços de Caldas"]'::jsonb,
    'pocos-de-caldas',
    'mock-circuito-caminhos-gerais'
  ),
  (
    'Caxambu divulga programação cultural para a próxima temporada',
    'mock-noticia-programacao-caxambu-2026',
    'A agenda fictícia destaca atrações culturais e espaços históricos do município.',
    '<p>Conteúdo demonstrativo para validar pesquisa, filtros por município e apresentação de matérias na interface.</p>',
    CURRENT_TIMESTAMP - INTERVAL '3 days',
    TRUE,
    'Cultura',
    'Redação de demonstração',
    '',
    '["demonstração", "cultura", "Caxambu"]'::jsonb,
    'caxambu',
    'mock-circuito-das-aguas'
  ),
  (
    'Camanducaia amplia opções de atividades ao ar livre',
    'mock-noticia-atividades-camanducaia-2026',
    'Roteiros fictícios de natureza e aventura ajudam a testar as notícias não destacadas.',
    '<p>Matéria fictícia para teste de dados da API. O conteúdo pode ser editado ou removido sem afetar os dados reais.</p>',
    CURRENT_TIMESTAMP - INTERVAL '5 days',
    FALSE,
    'Ecoturismo',
    'Redação de demonstração',
    '',
    '["demonstração", "natureza", "Camanducaia"]'::jsonb,
    'camanducaia',
    'mock-circuito-serras-verdes'
  ),
  (
    'São Lourenço prepara atividades de lazer para visitantes',
    'mock-noticia-lazer-sao-lourenco-2026',
    'Notícia demonstrativa para conferir a busca por município e a ordenação por data.',
    '<p>Texto de exemplo sem referência a uma publicação real. Use esta entrada apenas durante o desenvolvimento.</p>',
    CURRENT_TIMESTAMP - INTERVAL '8 days',
    FALSE,
    'Turismo',
    'Redação de demonstração',
    '',
    '["demonstração", "lazer", "São Lourenço"]'::jsonb,
    'sao-lourenco',
    'mock-circuito-das-aguas'
  )
) AS seed(
  title, slug, summary, content, published_at, is_featured, category,
  author, source_url, tags, cidade_slug, igr_slug
)
JOIN website_backend_cidade cidade ON cidade.slug = seed.cidade_slug
LEFT JOIN website_backend_igr igr ON igr.slug = seed.igr_slug
ON CONFLICT (slug) DO UPDATE SET
  title = EXCLUDED.title,
  summary = EXCLUDED.summary,
  content = EXCLUDED.content,
  published_at = EXCLUDED.published_at,
  is_featured = EXCLUDED.is_featured,
  category = EXCLUDED.category,
  author = EXCLUDED.author,
  source_url = EXCLUDED.source_url,
  tags = EXCLUDED.tags,
  cidade_id = EXCLUDED.cidade_id,
  igr_id = EXCLUDED.igr_id;

COMMIT;

-- Conferência dos registros do mock:
-- SELECT name, slug, start_date, end_date, cidade_id
-- FROM website_backend_evento WHERE slug LIKE 'mock-%' ORDER BY start_date;
--
-- SELECT title, slug, published_at, is_featured, cidade_id
-- FROM website_backend_noticia WHERE slug LIKE 'mock-%' ORDER BY published_at DESC;
--
-- SELECT name, slug FROM website_backend_igr WHERE slug LIKE 'mock-%' ORDER BY slug;
