# Auditoría: ¿se puede consultar el TUPA de las 28 municipalidades de la provincia de Huancayo?

**Fecha:** 10 de noviembre de 2026 · **Fuente:** Portal de Transparencia Estándar (PTE), sección *Planeamiento y organización* de cada municipalidad · **Datos:** [`auditoria_tupa_huancayo.csv`](auditoria_tupa_huancayo.csv)

## Método
1. Se identificaron las 28 municipalidades (la provincial y 27 distritales) en el PTE (`id_entidad` 1190 y 11082–11108).
2. En cada una se buscó el enlace al TUPA y se abrió su destino.
3. Si había PDF, se revisó si tiene texto digital o si son imágenes escaneadas (contando fuentes e imágenes del archivo).

## Resultados

| Situación | Municipalidades | % |
|---|---:|---:|
| ❌ No publica el TUPA en el PTE | 15 | 54 % |
| ❌ Enlace roto o inútil (Chilca, Viques) | 2 | 7 % |
| ⚠️ Desactualizado: TUPA de 2011 (Sicaya) | 1 | 4 % |
| ⚠️ Accesible con dificultad (Huayucachi, Hualhuas) | 2 | 7 % |
| ✅ Accesible | 8 | 29 % |

- **Solo 10 de 28** permiten llegar a un TUPA vigente desde el portal, y **4 de esos 10 son escaneos** o casi todo imágenes (Huayucachi, Huancán, Pilcomayo, San Jerónimo de Tunán): no se pueden buscar con Ctrl+F.
- **Solo 4 de 28 (14 %)** tienen un TUPA vigente, accesible y en texto digital: Huancayo (provincial), El Tambo, San Agustín de Cajas y Saño.

## Casos que ilustran el problema
- **Viques:** el enlace oficial apunta a `file:///C:/Users/…/Downloads/TUPA VIQUES - 2021.pdf`, es decir, a la computadora de un trabajador. Nadie más puede abrirlo.
- **Chilca:** el enlace dice "TUPA 2014" y lleva a la página de inicio de otra entidad, no a un documento.
- **Huayucachi:** el enlace principal está roto; el TUPA vigente (404 páginas escaneadas) está en un Google Drive enlazado con el nombre "Modificación de los procedimientos…".
- **Hualhuas:** el PDF publicado es una sola página que remite a un enlace de Google Drive.

## Límites
- Se revisó lo que cada municipalidad enlaza en el PTE, el canal oficial de transparencia. Alguna podría publicar su TUPA en otro lugar.
- El formato (texto o escaneo) se estimó a partir del contenido del PDF; "no determinado" significa que no se pudo concluir.
- Los archivos finales en Google Drive (Hualhuas) no se abrieron.

## Cobertura de Wayki
Wayki ya integra **las 8 municipalidades con TUPA vigente y legible**: Huancayo, El Tambo, San Agustín de Cajas, Saño, Sapallanga (digitales) y Huayucachi, Huancán, San Jerónimo de Tunán (escaneadas, con OCR). Quedan pendientes Pilcomayo (formato de tabla antiguo) y Hualhuas (archivo final en Drive). Sicaya no se incluye por tener un TUPA de 2011.

## Qué implica para Wayki
El problema no es solo de Huayucachi: en la provincia, **la mayoría de vecinos no puede consultar el TUPA de su municipalidad por internet**. Wayki puede funcionar con cualquier TUPA, escaneado o digital; el servicio a la municipalidad incluye **digitalizarlo y mantenerlo actualizado**, que es justo lo que pidió el encargado de modernización entrevistado.
