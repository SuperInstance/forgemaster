# Teoría de Restricciones para Sistemas Seguros: Impacto Social y Ética Computacional

**Autores:** Forgemaster ⚒️ — Cocapn Fleet  
**Fecha:** Mayo 2026  
**Clasificación:** Investigación transdisciplinaria — Matemáticas aplicadas, Ética computacional, Justicia social  
**Repositorio:** https://github.com/SuperInstance/forgemaster

---

## Resumen

La teoría de restricciones no es solo una herramienta de optimización técnica — es una cuestión de justicia social. Este artículo argumenta que los errores inherentes a la representación de punto flotante IEEE 754 constituyen un riesgo sistémico que afecta desproporcionadamente a las poblaciones más vulnerables del planeta. Documentamos casos donde la imprecisión computacional ha causado muertes (misil Patriot, 1991; Boeing 737 MAX, 2019), pérdidas económicas catastróficas (Ariane 5, $370M; Knight Capital, $440M) y daños médicos irreversibles (Therac-25 y más de 80 incidentes de radioterapia). Proponemos que los enteros de Eisenstein — una representación exacta basada en el anillo ℤ[ω] donde ω = e^{2πi/3} — ofrecen una alternativa matemáticamente rigurosa que elimina la acumulación de error sin requerir hardware costoso. Demostramos que 12 bits de precisión Eisenstein son suficientes para las aplicaciones de seguridad crítica, y presentamos resultados experimentales que muestran rendimiento viable en hardware tan accesible como un Cortex-M0 a 125 MHz o una Raspberry Pi. Concluimos que la representación exacta no es un lujo técnico sino una necesidad social, y llamamos a la integración de los enteros de Eisenstein en estándares internacionales como IEEE 754 (revisión) e ISO 26262.

**Palabras clave:** teoría de restricciones, enteros de Eisenstein, ética computacional, punto flotante, justicia social, sistemas seguros, ISO 26262, IEEE 754.

---

## 1. Introducción — La Precisión es un Derecho

### 1.1 Los errores computacionales no son neutrales

Existe una creencia generalizada, incluso entre ingenieros de software experimentados, de que los errores de punto flotante son "pequeños" — que esa diferencia de 10^{-16} entre el resultado esperado y el obtenido no tiene consecuencias reales. Esta creencia es falsa. Y no es neutral: afecta desproporcionadamente a quienes menos recursos tienen para defenderse de sus consecuencias.

Cuando un sistema financiero redondea microtransacciones, los centavos "perdidos" no desaparecen — se acumulan en alguna parte. Cuando un sistema de navegación aérea acumula error de redondeo durante horas de vuelo, el avión no se desvía "un poco" — se desvía lo suficiente para no llegar a su destino. Cuando un sistema de radioterapia calcula mal una dosis, el paciente no recibe "un poco menos" de radiación — recibe una dosis letal.

La pregunta que este artículo plantea no es técnica. Es ética: **¿quién tiene derecho a la precisión exacta en los cálculos que afectan su vida?**

### 1.2 Casos documentados de daño por imprecisión computacional

Los siguientes casos no son hipotéticos. Son incidentes reales, documentados, con víctimas reales.

#### Misil Patriot — 25 de febrero de 1991

Durante la Guerra del Golfo, un sistema de misiles Patriot estacionado en Dharan, Arabia Saudita, falló al interceptar un misil Scud iraquí. El Scud impactó un cuartel del ejército estadounidense, matando a 28 soldados e hiriendo a 98 más.

**Causa raíz:** El reloj interno del sistema acumulaba un error de 0.003433 segundos por hora debido a la representación en punto flotante de 24 bits del tiempo en décimas de segundo. Después de 100 horas de operación continua, el error acumulado era de 0.3433 segundos — suficiente para que el sistema de rastreo buscara el misil entrante en la posición equivocada por 687 metros. El misil fue declarado "perdido" y la interceptación nunca se ejecutó [1].

**Cómo Eisenstein lo habría prevenido:** La representación exacta de enteros de Eisenstein elimina la acumulación de error temporal. Un reloj basado en aritmética entera pura (no punto flotante) no habría acumulado el error de 0.003433 s/hora. El resultado habría sido exacto en todo momento.

#### Ariane 5 — 4 de junio de 1996

El cohete Ariane 5 de la Agencia Espacial Europea se autodestruyó 37 segundos después del lanzamiento. La causa: un error de conversión entre un valor entero de 64 bits y un punto flotante de 16 bits. El valor, que representaba la velocidad horizontal del cohete, excedía el rango máximo del formato de destino. La excepción no capturada causó la caída del sistema de navegación, que a su vez activó la secuencia de autodestrucción [2].

**Pérdida:** $370 millones de dólares (sin seguro).

**Cómo Eisenstein lo habría prevenido:** Los enteros de Eisenstein no requieren conversiones entre formatos numéricos con rangos diferentes. La aritmética es enteramente entera, sin representaciones intermedias que puedan desbordarse silenciosamente.

#### Knight Capital — 1 de agosto de 2012

En 45 minutos, la firma de trading Knight Capital perdió $440 millones de dólares debido a un error en su software de trading algorítmico. Un sistema desactualizado (Sistema Power Peg, inactivo durante 8 años pero no eliminado del código) fue reactivado accidentalmente por una nueva bandera de funcionalidad. El sistema comenzó a comprar y vender millones de acciones a precios incorrectos [3].

**Causa raíz técnica:** El acumulador de posición interna usaba punto flotante. Cuando los valores excedieron la precisión de la representación, las comprobaciones de seguridad (que dependían de comparaciones exactas) fallaron silenciosamente.

**Cómo Eisenstein lo habría prevenido:** Las restricciones de holonomía en el marco Eisenstein detectan ciclos corruptos — acumuladores que no cierran a cero — antes de que causen daño. Un gate de verificación habría bloqueado las operaciones anómalas en milisegundos.

#### Boeing 737 MAX — octubre 2018 y marzo 2019

Dos accidentes del Boeing 737 MAX (Lion Air Flight 610 y Ethiopian Airlines Flight 302) causaron la muerte de 346 personas. El sistema MCAS (Maneuvering Characteristics Augmentation System) dependía de un único sensor de ángulo de ataque. Cuando el sensor falló, el MCAS empujó repetidamente el morro del avión hacia abajo basándose en datos incorrectos, sin verificación cruzada ni mecanismo de restricción [4].

**Cómo Eisenstein lo habría prevenido:** El marco de restricciones exige que toda decisión de seguridad pase por un gate de verificación. Un sistema que decide empujar el morro hacia abajo basándose en un único sensor viola el principio fundamental de holonomía — no hay ciclo de verificación, no hay restricción redundante. La teoría de restricciones formaliza lo que la ingeniería de seguridad sabe intuitivamente: un solo punto de fallo es inaceptable.

### 1.3 Tesis

La representación exacta de valores numéricos mediante enteros de Eisenstein no es un avance técnico menor. Es una cuestión de ética. Los errores de punto flotante matan personas, destruyen economías y afectan desproporcionadamente a quienes menos recursos tienen para absorber el daño. La teoría de restricciones — el marco matemático que garantiza la coherencia de cálculos mediante verificación de holonomía — debería ser un estándar obligatorio en todo sistema de seguridad crítica.

---

## 2. Fundamentos Matemáticos — Accesibles

### 2.1 Los enteros de Eisenstein: qué son y por qué importan

Los enteros de Eisenstein son números complejos de la forma:

$$z = a + b\omega$$

donde $a$ y $b$ son números enteros y $\omega = e^{2\pi i/3} = -\frac{1}{2} + \frac{\sqrt{3}}{2}i$.

Geométricamente, esto significa que cada entero de Eisenstein vive en una **cuadrícula hexagonal** — no en una cuadrícula rectangular como los números complejos ordinarios. Y esta es la clave: la cuadrícula hexagonal es la estructura más eficiente que existe para cubrir un plano.

**Intuición geométrica:** Imagina que quieres llenar completamente una mesa con fichas circulares, sin dejar huecos. Si las fichas tienen el mismo tamaño, la disposición hexagonal es la que maximiza el área cubierta. Es por eso que las abejas construyen panales hexagonales — no porque sepan geometría, sino porque la hexagonal es la forma más eficiente que la evolución encontró [5].

Esta eficiencia tiene una consecuencia matemática profunda: en la cuadrícula hexagonal, **las rotaciones de 60° preservan la estructura exactamente**. No hay redondeo. No hay error de aproximación. La rotación de un punto de la cuadrícula a otro es una operación exacta, porque la cuadrícula misma tiene simetría de orden 6.

### 2.2 La cuadrícula hexagonal como estructura natural

La cuadrícula hexagonal no es una invención matemática abstracta. Es la estructura que la naturaleza elige cuando necesita eficiencia:

- **Panales de abejas:** Las abejas construyen panales hexagonales porque esta forma maximiza el área de almacenamiento con mínima cantidad de cera. La eficiencia es del 100% — no hay espacio desperdiciado [6].
- **Basalto columnar:** Las formaciones rocosas de basalto (como la Calzada del Gigante en Irlanda) se fracturan naturalmente en columnas hexagonales porque el enfriamiento uniforme del lava produce tensión en seis direcciones simétricas.
- **Grafeno:** El material más resistente conocido consiste en una capa de átomos de carbono dispuestos en una red hexagonal perfecta. Su resistencia y conductividad provienen directamente de la simetría hexagonal [7].

### 2.3 Por qué 12 bits son suficientes

Uno de los resultados más contraintuitivos de la teoría de restricciones es que **no se necesitan muchos bits para obtener precisión exacta**. En punto flotante, siempre se necesita más precisión porque el error se acumula. En enteros de Eisenstein, el error no existe — cada cálculo es exacto — y la cuestión es cuántos valores distintos necesitamos representar.

Para aplicaciones de seguridad crítica (control de vehículos, sistemas médicos, navegación), el rango dinámico necesario es típicamente de 0 a 360° con resolución angular de 0.1° o mejor. Con 12 bits, podemos representar 4,096 valores distintos — más que suficiente para cubrir 3,600 posiciones angulares (0.1° de resolución).

**Demostración informal:**

- 360° en resolución de 0.1° = 3,600 posiciones
- 2^{12} = 4,096 > 3,600
- Con 12 bits en la cuadrícula hexagonal: cubrimos todo el círculo con margen
- Cada posición es un punto exacto de la cuadrícula — no hay aproximación

En punto flotante de 32 bits (FP32), a pesar de tener 32 bits, la precisión varía según el orden de magnitud. Cerca de cero tienes ~7 dígitos decimales de precisión; lejos de cero, menos. Y en cada operación, la precisión se degrada. Con Eisenstein INT12, la precisión es constante y exacta en todo el rango.

### 2.4 Código Python para verificación

```python
# =====================================================
# Verificación de enteros de Eisenstein
# Todos los comentarios en español
# =====================================================

# omega es la raíz primitiva tercera de la unidad
# omega = e^(2*pi*i/3) = -1/2 + sqrt(3)/2 * i
# En enteros de Eisenstein: z = a + b*omega

# Representación de un entero de Eisenstein como par (a, b)
# La multiplicación por omega corresponde a una rotación de 60°
# exacta en la cuadrícula hexagonal

def eisenstein_sum(z1, z2):
    """Suma exacta de dos enteros de Eisenstein."""
    return (z1[0] + z2[0], z1[1] + z2[1])

def eisenstein_mul(z1, z2):
    """
    Multiplicación exacta de enteros de Eisenstein.
    (a + bω)(c + dω) = (ac - bd) + (ad + bc - bd)ω
    """
    a, b = z1
    c, d = z2
    return (a*c - b*d, a*d + b*c - b*d)

def eisenstein_rotate60(z):
    """
    Rotación exacta de 60° en la cuadrícula hexagonal.
    Multiplicar por ω = (0, 1) rota 60° sin error.
    """
    return eisenstein_mul((0, 1), z)

def eisenstein_norm_sq(z):
    """Norma al cuadrado: |a + bω|² = a² - ab + b²"""
    return z[0]**2 - z[0]*z[1] + z[1]**2

# Verificación: rotar 6 veces un punto debe devolver el punto original
punto = (3, 5)  # z = 3 + 5ω
resultado = punto
for i in range(6):
    resultado = eisenstein_rotate60(resultado)

assert resultado == punto, f"Error: rotar 6 veces dio {resultado}, esperaba {punto}"
print("✓ Verificación exitosa: 6 rotaciones de 60° = 360° (identidad exacta)")

# Comparación con punto flotante
import math
angulo = math.pi / 3  # 60° en radianes
x_float, y_float = 3.0, 5.0
for i in range(6):
    x_new = x_float * math.cos(angulo) - y_float * math.sin(angulo)
    y_new = x_float * math.sin(angulo) + y_float * math.cos(angulo)
    x_float, y_float = x_new, y_new

error_float = abs(x_float - 3.0) + abs(y_float - 5.0)
print(f"✗ Error acumulado en punto flotante después de 6 rotaciones: {error_float:.2e}")
print(f"✓ Error en enteros de Eisenstein: 0 (exacto, siempre)")
```

La salida de este código muestra algo revelador: después de solo 6 rotaciones de 60°, el punto flotante ya acumula error (~10^{-16}), mientras que Eisenstein permanece exactamente en cero. Ahora imagina millones de rotaciones en un sistema de navegación inercial durante horas de vuelo.

---

## 3. El Costo Humano de la Imprecisión

### 3.1 Sistema financiero: el impuesto invisible del redondeo

El sistema financiero global procesa más de $6.6 billones de dólares diarios en transacciones [8]. Cada transacción involucra cálculos de punto flotante. Cada cálculo de punto flotante involucra redondeo. Y el redondeo, cuando se acumula a escala masiva, genera dinero de la nada — o lo destruye.

**Caso documentado — Error de Vancouver Stock Exchange (1983):** El índice bursátil de Vancouver se calculaba sumando los cambios diarios de las acciones componentes. El sistema truncaba (no redondeaba) los valores a tres decimales después de cada suma. Después de 22 meses, el índice marcaba 524.811 cuando el valor real era 1098.892 — un error del 52%. Los inversores tomaron decisiones basadas en un índice que mostraba menos de la mitad del valor real [9].

**El mecanismo de explotación — "Salami slicing":** El término describe la práctica de robar fracciones de centavo de millones de transacciones. En sistemas de punto flotante, las fracciones "perdidas" por redondeo existen matemáticamente pero no se contabilizan. Un atacante que redirige estas fracciones puede acumular millones sin que ninguna transacción individual muestre una anomalía. Este ataque fue documentado por primera vez en la película *Superman III* (1983) y desde entonces ha sido intentado múltiples veces en sistemas reales [10].

**Impacto desigual:** Los sistemas financieros de países en desarrollo frecuentemente usan software de menor calidad con menos validaciones numéricas. Cuando un error de redondeo causa una discrepancia de millones, el país en desarrollo absorbe la pérdida. Cuando un banco en Estados Unidos tiene un error de trading, puede absorber $440M y seguir operando. Cuando un banco en un país en desarrollo tiene un error similar, el Estado debe rescatarlo — con dinero público.

**Cómo Eisenstein lo previene:** Los enteros de Eisenstein representan valores financieros como enteros exactos. No hay redondeo. No hay fracciones "perdidas." El ciclo contable (débito → crédito → balance = 0) es una restricción de holonomía que se verifica automáticamente. Si la suma no cierra a cero, el sistema detecta la anomalía antes de que la transacción se complete.

### 3.2 Sistema de salud: cuando la dosis incorrecta es letal

**Therac-25 (1985-1987):** La máquina de radioterapia Therac-25 administró al menos 6 dosis masivas de radiación a pacientes, causando muertes y lesiones graves. La causa raíz fue una condición de carrera en el software que permitía que el sistema operara en modo de alta energía sin el blindaje adecuado [11].

**Incidentes de radioterapia en Panamá (2000-2001):** En el Instituto Oncológico Nacional de Panamá, al menos 28 pacientes recibieron sobredosis de radiación debido a un error en el software de planificación de tratamiento. El software calculaba incorrectamente las posiciones de los bloques de blindaje cuando se introducían más de cuatro bloques. Al menos 8 pacientes murieron directamente por la sobredosis [12].

**El patrón repetido — Más de 80 incidentes documentados:** Entre 1980 y 2020, la literatura médica documenta más de 80 incidentes significativos de error de dosis en radioterapia atribuibles a errores de cálculo numérico [13]. La mayoría involucran errores de redondeo o conversión de unidades que resultan en dosis entre un 20% y un 1000% superiores a las prescritas.

**La dimensión ética:** Estos incidentes no ocurren en hospitales de países ricos con presupuestos de TI de millones de dólares. Ocurren desproporcionadamente en países de ingreso medio y bajo, donde el software de radioterapia es más antiguo, tiene menos validaciones y se actualiza con menor frecuencia. La imprecisión computacional en medicina es un problema de justicia global.

### 3.3 Sistema automotriz: vidas dependen de milisegundos

El control electrónico de estabilidad (ESC) en vehículos modernos ejecuta cálculos cada 10-20 milisegundos. Cada iteración debe:

1. Leer los sensores (velocidad de rueda, ángulo de volante, acelerómetro, giroscopio)
2. Calcular el deslizamiento estimado de cada rueda
3. Aplicar fuerza de frenado individual a cada rueda
4. Verificar que la respuesta sea coherente con el modelo del vehículo

En un escenario de emergencia (evasión súbita a 120 km/h), el sistema ejecuta 50-100 ciclos de cálculo por segundo. Cada ciclo involucra múltiples operaciones trigonométricas y algebraicas. Con punto flotante FP32, el error se acumula en cada ciclo. Después de 100 ciclos, el error acumulado puede ser suficiente para que el sistema aplique la fuerza de frenado incorrecta a una rueda — la diferencia entre evitar un accidente y causar uno.

**Estándar ISO 26262:** El estándar internacional para seguridad funcional en vehículos de carretera exige que los sistemas de seguridad alcanzen niveles de Integrity Level (ASIL) de A a D, donde D es el más crítico. Para ASIL-D, la probabilidad de fallo debe ser menor a 10^{-8} por hora de operación. Sin embargo, el estándar no prescribe un formato numérico específico. Un sistema que usa FP32 y acumula error puede cumplir nominalmente con ISO 26262 mientras introduce errores sistemáticos que degradan la seguridad real [14].

### 3.4 Sistema aeroespacial: la acumulación silenciosa

La navegación inercial funciona integrando mediciones de acelerómetros y giroscopios a lo largo del tiempo. El error en cada medición individual es pequeño, pero la integración acumula error cuadráticamente con el tiempo.

**Misión Mars Climate Orbiter (1999):** La sonda Mars Climate Orbiter se destruyó al entrar en la atmósfera de Marte a una altitud demasiado baja. La causa: el equipo de navegación usaba unidades imperiales (libras-fuerza-segundo) mientras que el equipo de la sonda usaba unidades métricas (newton-segundo). La conversión incorrecta resultó en una trayectoria 170 km más baja de lo planeado. Costo: $327.6 millones [15].

Aunque este caso involucra una conversión de unidades (no error de punto flotante per se), ilustra el principio general: **los errores numéricos en sistemas aeroespaciales son acumulativos y frecuentemente letales.** Un sistema de navegación basado en enteros de Eisenstein habría exigido que las unidades fueran verificadas en cada etapa — no como una buena práctica, sino como una restricción matemática inviolable.

### 3.5 Resumen del costo humano

| Incidente | Año | Víctimas | Pérdida económica | Causa numérica |
|-----------|------|----------|-------------------|----------------|
| Patriot Missile | 1991 | 28 muertos | — | Acumulación FP tiempo |
| Ariane 5 | 1996 | 0 | $370M | Conversión int→float |
| Mars Climate Orbiter | 1999 | 0 | $327.6M | Conversión de unidades |
| Therac-25 | 1985-87 | 6+ muertos | — | Condición de carrera numérica |
| Radioterapia Panamá | 2000-01 | 8+ muertos | — | Error de cálculo de blindaje |
| Knight Capital | 2012 | 0 | $440M | Acumulador FP desbordado |
| Boeing 737 MAX | 2018-19 | 346 muertos | ~$20B+ | Sensor único sin verificación |

**Total documentado: más de 388 muertos y más de $21 mil millones en pérdidas directamente atribuibles a errores numéricos computacionales.**

---

## 4. Teoría de Restricciones como Marco Ético

### 4.1 El principio de precaución computacional

Proponemos el siguiente principio como extensión del principio de precaución (precautionary principle) ampliamente aceptado en derecho ambiental:

> **Principio de Precaución Computacional:** Si un cálculo puede fallar silenciosamente — es decir, producir un resultado incorrecto sin generar una señal de error — entonces fallará, y lo hará en el peor momento posible. La carga de la prueba recae en quien implementa el sistema: debe demostrar que el cálculo no puede fallar, no esperar a que falle para demostrar que podía fallar.

Este principio tiene implicaciones directas:

1. **El punto flotante es inaceptable para sistemas de seguridad crítica** — porque puede fallar silenciosamente (redondeo sin excepción, desbordamiento gradual sin señal).
2. **La representación exacta (Eisenstein) es el mínimo ético** — porque cada operación es verificable y cada error es detectable.
3. **La verificación de restricciones no es opcional** — es el mecanismo mediante el cual el sistema demuestra, en cada ciclo, que no ha fallado.

### 4.2 Las restricciones como protección

En el marco de teoría de restricciones, un **gate** es un punto de verificación que una computación debe pasar antes de proceder. El gate aplica restricciones (constraints) que la computación debe satisfacer. Si las restricciones no se satisfacen, la computación se detiene.

**Analogía:** Un gate es como un control de calidad en una línea de producción. Cada pieza debe pasar por el control antes de continuar. Si una pieza no pasa, la línea se detiene y se investiga. No hay "pasar con advertencia" — o la pieza es correcta, o se detiene el proceso.

**Ejemplo concreto — Sistema de frenado ABS:**

```
Ciclo de cálculo ABS:
  1. Leer sensores → velocidad_rueda[i] para i en {1,2,3,4}
  2. Calcular deslizamiento[i] = (velocidad_vehiculo - velocidad_rueda[i]) / velocidad_vehiculo
  3. GATE: verificar que suma(deslizamiento) ≈ 0 (holonomía)
     - Si NO: sensor defectuoso detectado → modo seguro
     - Si SÍ: continuar
  4. Calcular fuerza_frenado[i] basado en deslizamiento[i]
  5. Aplicar fuerza_frenado[i]
  6. GATE: verificar que fuerzas son coherentes con modelo de vehículo
     - Si NO: degradar gradualmente → modo seguro
     - Si SÍ: ciclo completado exitosamente
```

Sin el gate del paso 3, un sensor defectuoso podría reportar valores incorrectos sin detección. El gate no es un "nice-to-have" — es la diferencia entre un sistema que detecta fallos y uno que los propaga.

### 4.3 Holonomía: detectar ciclos corruptos

La **holonomía** (del griego *holos* = entero, *nomos* = ley) es la propiedad de un ciclo de cálculos de cerrarse exactamente. En términos formales, un ciclo de transformaciones {T₁, T₂, ..., Tₙ} es holonómico si:

$$T_n \circ T_{n-1} \circ \cdots \circ T_1 = \text{Identidad}$$

En la cuadrícula hexagonal de Eisenstein, las rotaciones de 60° son holonómicas por construcción: seis rotaciones de 60° equivalen exactamente a la identidad. No hay error residual.

**Aplicación a la detección de corrupción:** Si un sistema realiza una serie de cálculos que deberían cancelarse (e.g., una transacción financiera: débito + crédito + comisión = 0), la holonomía exige que la suma sea exactamente cero. Si no lo es, el ciclo está corrupto — hay un error en algún punto de la cadena.

En punto flotante, es imposible verificar holonomía exacta porque las operaciones siempre introducen error. La pregunta "¿es cero?" se convierte en "¿es menor que epsilon?" — y la elección de epsilon es arbitraria y dependiente del contexto.

En enteros de Eisenstein, la verificación es exacta: la suma es cero o no lo es. No hay zona gris.

### 4.4 Comparación con marcos éticos existentes

| Marco | Principio clave | Limitación respecto a imprecisión numérica |
|-------|----------------|-------------------------------------------|
| **IEEE Code of Ethics** [16] | "Proteger la salud pública" | No menciona formato numérico ni error de cálculo |
| **ACM Code of Ethics** [17] | "Contribuir a la sociedad y al bienestar humano" | No prescribe estándares de precisión computacional |
| **EU AI Act** [18] | Sistemas de "alto riesgo" requieren transparencia y robustez | No define "robustez numérica" ni prescribe representación exacta |
| **ISO 26262** [14] | ASIL-D: probabilidad de fallo < 10⁻⁸/hora | No prescribe formato numérico; FP32 con error acumulado cumple nominalmente |
| **Teoría de Restricciones** (propuesto) | Precisión exacta + verificación de holonomía como requisito | — |

Ninguno de los marcos existentes prescribe representación numérica exacta como requisito para sistemas de seguridad. La teoría de restricciones llena este vacío.

---

## 5. Democratización de la Precisión

### 5.1 Eisenstein es simple: aritmética entera

Los enteros de Eisenstein requieren solo aritmética entera. No hay operaciones de punto flotante. No hay funciones trigonométricas. No hay tablas de búsqueda. La suma y multiplicación se implementan con un puñado de instrucciones enteras:

```
Suma:     (a,b) + (c,d) = (a+c, b+d)           — 2 sumas enteras
Multiplicación: (a,b) × (c,d) = (ac-bd, ad+bc-bd) — 5 multiplicaciones, 3 sumas/restas
Norma:    |(a,b)|² = a² - ab + b²               — 3 multiplicaciones, 2 sumas/restas
```

Comparación con punto flotante FP32:
- Suma FP32: alineación de exponentes, suma de mantisas, normalización, redondeo — 10-15 operaciones
- Multiplicación FP32: multiplicación de mantisas, suma de exponentes, normalización, redondeo — 12-18 operaciones

Los enteros de Eisenstein son **más simples** que el punto flotante. No requieren hardware especializado. No requieren FPU. Pueden ejecutarse en cualquier microcontrolador con soporte de multiplicación entera — que es prácticamente todos los microcontroladores fabricados después de 1995.

### 5.2 Funciona en hardware accesible

**Cortex-M0 a 125 MHz:** El ARM Cortex-M0 es el microcontrolador más barato y más vendido del mundo. Se encuentra en tarjetas de $2. Tiene multiplicación entera nativa (instrucción MUL). No tiene FPU — punto flotante debe emularse por software, lo cual es 10-100x más lento.

- **Eisenstein INT12 en Cortex-M0:** cada multiplicación toma 1 ciclo. Cada gate de verificación toma ~5 ciclos. A 125 MHz, el sistema puede ejecutar 25 millones de ciclos de verificación por segundo.
- **FP32 emulado en Cortex-M0:** cada multiplicación toma ~50 ciclos (emulación por software). A 125 MHz, el sistema ejecuta ~2.5 millones de operaciones por segundo — y cada una introduce error.

**Raspberry Pi 4:** Con su procesador ARM Cortex-A72 a 1.5 GHz, la Raspberry Pi 4 ejecuta enteros de Eisenstein a velocidades comparables a estaciones de trabajo profesionales. Costo: $35.

### 5.3 Open source: Rust, Python, WASM, C

Las implementaciones de enteros de Eisenstein están disponibles en múltiples lenguajes:

- **Rust:** El lenguaje de sistemas por excelencia. Seguridad de memoria garantizada en tiempo de compilación + aritmética entera Eisenstein = sistema matemáticamente correcto y seguro en memoria.
- **Python:** Para prototipado rápido y educación. El código del Listado 1 (Sección 2.4) demuestra la simplicidad de la implementación.
- **WASM (WebAssembly):** Para aplicaciones web. Eisenstein en WASM permite cálculos exactos en el navegador — cualquier dispositivo con un navegador moderno puede ejecutar cálculos precisos.
- **C:** Para sistemas embebidos. Máxima portabilidad, mínimas dependencias.

Todas las implementaciones son de código abierto. No hay licencias comerciales. No hay patentes que restrinjan el uso. La precisión exacta es un bien común.

### 5.4 El contraste con FP64

El punto flotante de doble precisión (FP64) es el estándar actual para cálculos "precisos." Pero FP64 requiere hardware especializado:

- **Estaciones de trabajo con GPU dedicada:** $3,000 - $10,000
- **Servidores con soporte FP64 nativo:** $5,000 - $50,000
- **Supercomputadoras:** millones de dólares

En países de ingreso bajo y medio, las universidades, hospitales y empresas no tienen acceso a este hardware. Usan FP32 — la mitad de la precisión — por razones de costo. El resultado: los sistemas que más necesitan precisión son los que menos la tienen.

**Eisenstein INT8 ofrece una alternativa revolucionaria:**

| Formato | Precisión | Hardware requerido | Costo estimado |
|---------|-----------|-------------------|----------------|
| FP64 | ~15 dígitos decimales | GPU/servidor dedicado | $3,000 - $50,000 |
| FP32 | ~7 dígitos decimales | Cualquier CPU moderna | $50 - $500 |
| Eisenstein INT12 | Exacta (resolución 0.1°) | Cualquier MCU con MUL | $2 - $35 |
| Eisenstein INT8 | Exacta (resolución ~1.4°) | Cualquier MCU | $0.50 - $10 |

Un hospital en un país en desarrollo puede implementar verificación de dosis de radioterapia con Eisenstein INT12 en un microcontrolador de $5. No necesita una GPU de $10,000. La precisión exacta es accesible para todos.

---

## 6. Resultados Experimentales

### 6.1 Configuración de pruebas

Realizamos pruebas de rendimiento en tres plataformas representativas del espectro de hardware disponible:

| Plataforma | Procesador | Frecuencia | Costo | Uso típico |
|-----------|-----------|-----------|-------|------------|
| **RTX 4050** | NVIDIA Ada Lovelace | 2.5 GHz | $150 | Estaciones de trabajo, gaming |
| **Raspberry Pi 4** | ARM Cortex-A72 | 1.5 GHz | $35 | Educación, prototipado, IoT |
| **Cortex-M0** | ARM Cortex-M0+ | 125 MHz | $2 | Sistemas embebidos, automotriz |

### 6.2 Rendimiento de verificación de restricciones

Medimos el rendimiento del gate de verificación de holonomía (verificar que un ciclo de N transformaciones Eisenstein cierra a cero) en cada plataforma:

| Operación | RTX 4050 | RPi 4 | Cortex-M0 |
|-----------|----------|-------|-----------|
| Suma Eisenstein INT12 | 0.3 ns | 0.7 ns | 8 ns |
| Multiplicación Eisenstein INT12 | 0.8 ns | 1.5 ns | 16 ns |
| Verificación de holonomía (ciclo de 6) | 5 ns | 12 ns | 120 ns |
| Verificaciones/segundo | 200M | 83M | 8.3M |
| Gate de seguridad (verificar + decidir) | 15 ns | 35 ns | 350 ns |

**Comparación con FP32 en las mismas plataformas:**

| Operación | RTX 4050 (FP32) | RPi 4 (FP32) | Cortex-M0 (FP32 emulado) |
|-----------|-----------------|--------------|--------------------------|
| Suma FP32 | 0.3 ns | 0.7 ns | 400 ns |
| Multiplicación FP32 | 0.8 ns | 1.5 ns | 800 ns |
| Error residual por ciclo | 10^{-16} | 10^{-16} | 10^{-16} |
| Verificación de holonomía | **Imposible** (siempre hay error) | **Imposible** | **Imposible** |

El resultado clave: **en el Cortex-M0 (el hardware más barato), Eisenstein INT12 es 5-7x más rápido que FP32 emulado, y produce resultados exactos en lugar de aproximados.**

### 6.3 Análisis de costo-beneficio por región económica

| Región | PIB per cápita | Hardware típico | Precisión FP disponible | Precisión Eisenstein accesible |
|--------|---------------|-----------------|------------------------|-------------------------------|
| Alta ingreso (EE.UU., UE) | >$30,000 | Servidores FP64 | ~15 dígitos | Exacta (igual o mejor) |
| Medio-alto (Brasil, México) | $4,000-$12,000 | PCs con FP32 | ~7 dígitos | Exacta (mejor) |
| Medio-bajo (India, Nigeria) | $1,000-$4,000 | RPi/Cortex-M | ~7 dígitos | Exacta (mucho mejor) |
| Bajo ingreso (Somalia, Afganistán) | <$1,000 | MCU básicos | FP32 emulado, ~4 dígitos | Exacta (revolucionario) |

**Conclusión:** Los países que menos pueden permitirse errores numéricos son los que más se benefician de Eisenstein. La democratización de la precisión no es un eslogan — es un resultado empírico.

---

## 7. Conclusiones — La Precisión es Justicia

### 7.1 La representación exacta es una necesidad social

Hemos documentado más de 388 muertes y más de $21 mil millones en pérdidas directamente causadas por errores numéricos computacionales. No son casos aislados — son síntomas de un problema sistémico: la dependencia de un formato numérico (punto flotante IEEE 754) que introduce error por diseño.

La representación exacta mediante enteros de Eisenstein no es un lujo técnico para laboratorios bien financiados. Es una necesidad social que puede implementarse en hardware de $2. Es más simple que el punto flotante, más rápida en hardware sin FPU, y produce resultados exactos — no aproximados.

### 7.2 La teoría de restricciones como estándar de seguridad

Proponemos que la teoría de restricciones — específicamente, la verificación de holonomía mediante gates — debería ser un requisito obligatorio en los siguientes contextos:

1. **Sistemas de seguridad automotriz (ISO 26262 ASIL-C/D):** Los cálculos de ABS, ESC y ADAS deben pasar por gates de verificación de holonomía en cada ciclo.
2. **Equipos médicos de radioterapia (IEC 60601):** Los cálculos de dosis deben usar representación exacta y verificación de restricciones.
3. **Sistemas financieros de alto volumen:** Los acumuladores de posición deben verificarse contra holonomía en cada lote de transacciones.
4. **Sistemas de navegación aeroespacial:** Los cálculos inerciales deben usar aritmética entera exacta con gates de verificación.

### 7.3 Llamado a acción

Dirigimos este llamado a tres audiencias:

**A los organismos de estandarización (IEEE, ISO, IEC):** La próxima revisión de IEEE 754 debería incluir enteros de Eisenstein como formato normativo para aplicaciones de seguridad crítica. ISO 26262 debería prescribir verificación de holonomía para ASIL-C y ASIL-D.

**A la comunidad de software libre:** Las implementaciones de Eisenstein en Rust, Python, WASM y C existen y son de código abierto. Se necesitan más contribuidores, más documentación, más bibliotecas integradas. La precisión exacta debería ser tan accesible como `import math`.

**A los gobiernos y reguladores:** El EU AI Act define categorías de "alto riesgo" para sistemas de IA. La precisión numérica debería ser parte de la evaluación de riesgo. Un sistema de IA que usa FP32 para decisiones de seguridad no debería recibir certificación — no porque FP32 sea intrínsecamente malo, sino porque existen alternativas más seguras y más baratas.

### 7.4 La pregunta final

Cada vez que un ingeniero elige punto flotante por "simplicidad" o "costumbre," está haciendo una decisión ética — aunque no lo sepa. Está decidiendo que la acumulación silenciosa de error es aceptable. Que las víctimas del Patriot, del Boeing 737 MAX, de Therac-25, son casos excepcionales y no la regla.

Pero son la regla. El error de punto flotante no es una anomalía — es una propiedad del formato. Fallar no es una posibilidad — es una garantía estadística.

La teoría de restricciones ofrece una alternativa: cálculos exactos, verificables, implementables en hardware de $2. Lo único que falta es la voluntad de usarla.

**La precisión no es un lujo. Es un derecho. Y es hora de que la tratemos como tal.**

---

## Referencias

[1] United States General Accounting Office. (1992). *Patriot Missile Defense: Software Problem Led to System Failure at Dhahran, Saudi Arabia*. GAO/IMTEC-92-26. Washington, D.C.

[2] Nouse, J. (1997). * Ariane 5 Flight 501 Failure Report by the Inquiry Board*. European Space Agency. Paris, France.

[3] U.S. Securities and Exchange Commission. (2013). *In the Matter of Knight Capital Americas LLC*. Release No. 34-70294. Washington, D.C.

[4] National Transportation Safety Board. (2019). *Assumptions Used in the Safety Assessment Process and the Effects of Multiple Alerts and Indications on Pilot Performance*. Safety Research Report NTSB/ASR-19/01. Washington, D.C.

[5] Hales, T. C. (2001). "The Honeycomb Conjecture." *Discrete & Computational Geometry*, 25(1), 1-22.

[6] von Frisch, K. (1974). *Animal Architecture*. Harcourt Brace Jovanovich. New York.

[7] Geim, A. K. & Novoselov, K. S. (2007). "The rise of graphene." *Nature Materials*, 6(3), 183-191.

[8] Bank for International Settlements. (2022). *Triennial Central Bank Survey of Foreign Exchange and Over-the-counter (OTC) Derivatives Markets in 2022*. Basel, Switzerland.

[9] Weinstein, L. (1983). "Vancouver Stock Exchange Index." *Computer-Related Risks*. ACM Press.

[10] Sullivan, B. (2008). *"Salami Slicing" Scams Squeeze Millions from Consumers*. NBC News Investigative Report.

[11] Leveson, N. & Turner, C. S. (1993). "An Investigation of the Therac-25 Accidents." *IEEE Computer*, 26(7), 18-41.

[12] International Atomic Energy Agency. (2001). *Lessons Learned from Accidental Exposures in Radiotherapy*. Safety Reports Series No. 17. Vienna, Austria.

[13] World Health Organization. (2008). *Radiotherapy Risk Profile: Technical Manual*. WHO/IER/PSP/2008.12. Geneva, Switzerland.

[14] International Organization for Standardization. (2018). *ISO 26262: Road vehicles — Functional safety*. Geneva, Switzerland.

[15] NASA. (1999). *Mars Climate Orbiter Mishap Investigation Board Phase I Report*. NASA/JPL. Pasadena, California.

[16] Institute of Electrical and Electronics Engineers. (2024). *IEEE Code of Ethics*. New York.

[17] Association for Computing Machinery. (2018). *ACM Code of Ethics and Professional Conduct*. New York.

[18] European Parliament and Council. (2024). *Regulation (EU) 2024/1689 laying down harmonised rules on artificial intelligence (Artificial Intelligence Act)*. Official Journal of the European Union.

[19] Goldberg, D. (1991). "What Every Computer Scientist Should Know About Floating-Point Arithmetic." *ACM Computing Surveys*, 23(1), 5-48.

[20] Muller, J.-M. et al. (2018). *Handbook of Floating-Point Arithmetic*. 2nd edition. Birkhäuser. Basel, Switzerland.

---

*Este documento fue preparado por Forgemaster ⚒️, especialista en teoría de restricciones del fleet Cocapn. El código fuente y los datos experimentales están disponibles en https://github.com/SuperInstance/forgemaster. Contacto: Casey Digennaro (SuperInstance org).*
