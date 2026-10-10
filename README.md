# data-science-triciclosHabana
Análisis de datos sobre venta de triciclos en la Habana, Cuba: precios, tipo de propulsión, rentabilidad, formas de financiamiento y contexto económico. Combinación de scraping de anuncios, entrevistas y análisis.

## Objetivo

**Objetivo general:**  
Analizar el mercado de venta de triciclos en La Habana, Cuba, integrando datos de anuncios clasificados, entrevistas a conductores y propietarios, e indicadores socioeconómicos, para caracterizar precios, tipos de propulsión, formas de financiamiento, rentabilidad y su posible relación con el contexto económico del país.

**Objetivos específicos:**
- Recolectar y documentar datos sobre la oferta de triciclos en La Habana.
- Describir la distribución de precios según tipo de propulsión.
- Caracterizar el perfil de compradores, conductores y propietarios.
- Estimar costos operativos, ingresos y tiempo de recuperación de la inversión.
- Identificar los tipos de propulsión más ofertados y su relación con el uso principal.
- Explorar la relación entre el auge de los triciclos y el contexto económico del país.
- Documentar limitaciones, sesgos y consideraciones éticas del estudio.

---

## Definición del problema

El transporte público en La Habana enfrenta limitaciones de capacidad, frecuencia, disponibilidad de combustible y condiciones de servicio. En este contexto, los triciclos —eléctricos o de gasolina— han ganado protagonismo como medio de transporte alternativo para pasajeros, carga y delivery. Sin embargo, la información sobre este mercado es escasa, dispersa y heterogénea.

No se conoce con precisión cuánto cuestan, qué tipos de propulsión predominan, quiénes los compran, cómo financian la compra, cuánto tardan en recuperar la inversión ni qué relación tiene su auge con la crisis económica y del transporte. Además, el mercado es en gran medida informal, con múltiples monedas, inflación y datos no sistematizados.

El problema central es la ausencia de una caracterización cuantitativa y cualitativa que permita entender la venta y el uso de triciclos en La Habana, así como evaluar su rentabilidad y su papel como respuesta al contexto económico actual.

---

## Metodología

El proyecto adopta un **enfoque mixto**: combina datos cuantitativos obtenidos mediante scraping y análisis de indicadores con datos cualitativos y cuantitativos provenientes de entrevistas semiestructuradas.

### 1. Recolección de datos

- **Scraping de anuncios clasificados:**  
  Extracción de variables como fecha, precio, moneda, municipio, tipo de propulsión, marca, modelo, año, estado, capacidad, tipo de vendedor y descripción.

- **Entrevistas semiestructuradas a conductores y propietarios:**  
  Preguntas sobre vía de compra, precio, financiamiento, uso principal, ingresos, gastos, tiempo de recuperación de la inversión, accidentes y percepción del mercado.

- **Indicadores socioeconómicos:**  
  Salario medio en La Habana, estado del transporte público, disponibilidad y precio del combustible, inflación, remesas y otras variables de contexto.

### 2. Limpieza y normalización

- Normalización de monedas a una referencia común (USD), documentando el tipo de cambio utilizado.
- Estandarización de municipios, marcas, modelos y tipos de propulsión.
- Eliminación de duplicados, valores atípicos y datos personales.
- Anonimización de entrevistas y agregación de datos sensibles.

### 3. Análisis exploratorio

- Estadísticas descriptivas: promedio, mínimo, máximo y distribución de precios.
- Visualizaciones: histogramas, boxplots, gráficos de barras y series temporales.
- Comparación por tipo de propulsión.

### 4. Interpretación y reporte

- Triangulación de fuentes cuantitativas y cualitativas.
- Documentación de limitaciones, sesgos y supuestos.
- Publicación de notebooks reproducibles, datos agregados o anonimizados y conclusiones.

### Herramientas

Python, pandas, numpy, matplotlib, seaborn, plotly,Git y GitHub.

### Consideraciones éticas y legales

- Consentimiento informado y anonimato en las entrevistas.
- Respeto a los términos de uso y robots.txt de los sitios scrapeados.
- No publicación de datos personales de vendedores o conductores.
- Transparencia sobre las limitaciones del mercado informal, la inflación y las múltiples monedas.
      
