INSERT INTO schools (id, name) VALUES
  ('ce03b093-2513-428f-bd79-0bddc2e8d2e2', 'Escuela Náutica Mistral');

INSERT INTO courses (id, name, documents) VALUES
  ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Patrón de Embarcación de Recreo (PER)', '{"tests":[{"id":1,"name":"Test 1 - Navegación Básica","file":"test-01-navegacion.json","questions":30},{"id":2,"name":"Test 2 - Meteorología","file":"test-02-meteorologia.json","questions":25}],"apuntes":[{"id":1,"name":"Tema 1 - Introducción a la navegación","file":"tema-01-introduccion.pdf","pages":45},{"id":2,"name":"Tema 2 - Meteorología y mar","file":"tema-02-meteorologia.pdf","pages":38}],"examenes":[{"id":1,"name":"Examen Oficial Junio 2023","file":"examen-2023-06.pdf","questions":50}],"documentos":[]}');

INSERT INTO registration_codes (code, school_id, course_id) VALUES
  ('TEST', 'ce03b093-2513-428f-bd79-0bddc2e8d2e2', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890');
