# Mejoras pendientes para generate_cards.py

## Cambios implementados en próximo commit:

### 1. ✅ Fuentes más grandes (Philip's feedback)
- Aumentar tamaño de fuente base de 7pt → 10pt
- Mejorar legibilidad en celdas

### 2. ✅ Header para pub branding (Philip's feedback)
- Espacio reservado en top para logo del pub
- Texto: "Follow us: @pubname | facebook.com/pubname"
- Placeholder si no hay logo

### 3. ✅ Logo Perfect DJ en casilla FREE (Philip's feedback)
- Centrado en la casilla FREE
- Tamaño más visible

### 4. ✅ Información de premios (Philip's feedback)
- Agregar texto en footer/lateral:
  * "Prizes For:"
  * "✓ All 4 Corners"
  * "✓ First Line"  
  * "✓ Full House!"

### 5. ✅ Bordes redondeados (Philip's feedback)
- FPDF2 tiene soporte limitado para rounded corners
- Alternativa: Bordes bold en las 4 esquinas del grid
- Usar líneas más gruesas en bordes externos

## Próximos pasos:
1. Modificar create_bingo_card() para aumentar font sizes
2. Agregar pub_branding_header()
3. Agregar prizes_footer()
4. Bold borders en grid exterior
5. Ajustar CELL_HEIGHT para acomodar fuentes más grandes
