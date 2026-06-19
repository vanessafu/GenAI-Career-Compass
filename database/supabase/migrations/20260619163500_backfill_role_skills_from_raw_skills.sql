WITH split_raw_skills AS (
    SELECT
        c.role_id,
        btrim(raw_skill.skill_name) AS skill_name,
        regexp_replace(
            lower(btrim(raw_skill.skill_name)),
            '[^a-z0-9+#]+',
            ' ',
            'g'
        ) AS normalized_raw_skill
    FROM career_roles c
    CROSS JOIN LATERAL regexp_split_to_table(c.raw_skills, '\s*,\s*') AS raw_skill(skill_name)
    WHERE c.raw_skills IS NOT NULL
      AND btrim(c.raw_skills) <> ''
),
normalized_role_skills AS (
    SELECT DISTINCT
        srs.role_id,
        srs.skill_name,
        COALESCE(sa.canonical_key, regexp_replace(srs.normalized_raw_skill, '\s+', ' ', 'g')) AS normalized_skill_name
    FROM split_raw_skills srs
    LEFT JOIN skill_aliases sa ON sa.alias_key = regexp_replace(srs.normalized_raw_skill, '\s+', ' ', 'g')
    WHERE srs.skill_name <> ''
      AND srs.normalized_raw_skill <> ''
)
INSERT INTO role_skills (
    role_id,
    skill_name,
    normalized_skill_name
)
SELECT
    role_id,
    skill_name,
    normalized_skill_name
FROM normalized_role_skills
ON CONFLICT (role_id, skill_name) DO UPDATE SET
    normalized_skill_name = EXCLUDED.normalized_skill_name;
