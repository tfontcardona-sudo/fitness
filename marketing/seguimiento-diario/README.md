# Campaña «Supervisado a diario» (agosto 2026)

20 piezas premium para Instagram — 11 posts (1080×1350) y 9 stories
(1080×1920) — hechas con las 4 fotos reales del coach (marketing/oferta-1eur)
y maquetas de la app real. Tono: asesoría cercana y SUPERVISADA A DIARIO,
con ganchos visuales e informativos y las dos formas reales de pagar la
oferta. Todas cierran a app.dqrassessories.com.

## Orden de publicación sugerido (2-3 por semana)
1. p01 portada (autoridad) → 2. p02 story gancho → 3. p06 app →
4. p04 story cercanía → 5. p10 método → 6. p07 story diario →
7. p11 comparativa → 8. p08 entreno → 9. p09 story revisión →
10. p13 anamnesis → 11. p12 story anti-venta → 12. p05 semana →
13. p14 story progreso → 14. p15 credencial → 15. p03 quién mira →
16. p16 story 1 € → 17. p17 dos formas de pago → 18. p18 story plazas →
19. p20 story FAQ → 20. p19 cierre.

## Regenerar o retocar una pieza
Los HTML de `fuentes/` son la verdad; el texto se edita ahí y se re-renderiza:

    ./render.sh fuentes/p05-post-semana.html

(Requiere Chromium headless — variable CHROME — y las tipografías Anton,
Archivo y Fraunces instaladas; el CSS también las importa de Google Fonts.)
El render produce PNG; las piezas finales del repo están en JPG (calidad 92).
