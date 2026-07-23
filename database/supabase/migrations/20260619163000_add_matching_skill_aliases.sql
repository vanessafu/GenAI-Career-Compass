INSERT INTO skill_aliases (
    alias_key,
    alias_display,
    canonical_key,
    canonical_display
)
VALUES
    ('api', 'API', 'rest apis', 'REST APIs'),
    ('apis', 'APIs', 'rest apis', 'REST APIs'),
    ('rest api', 'REST API', 'rest apis', 'REST APIs'),
    ('restful api', 'RESTful API', 'restful apis', 'RESTful APIs'),
    ('spring', 'Spring', 'spring framework', 'Spring Framework'),
    ('spring boot', 'Spring Boot', 'spring framework', 'Spring Framework'),
    ('ux', 'UX', 'ui ux design', 'UI/UX Design'),
    ('ui', 'UI', 'ui ux design', 'UI/UX Design'),
    ('accessibility', 'Accessibility', 'web accessibility guidelines', 'Web Accessibility Guidelines'),
    ('a11y', 'A11y', 'web accessibility guidelines', 'Web Accessibility Guidelines'),
    ('analytics', 'Analytics', 'data analysis', 'Data Analysis'),
    ('data analytics', 'Data Analytics', 'data analysis', 'Data Analysis')
ON CONFLICT (alias_key) DO UPDATE SET
    alias_display = EXCLUDED.alias_display,
    canonical_key = EXCLUDED.canonical_key,
    canonical_display = EXCLUDED.canonical_display;
