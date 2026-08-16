"""TIENDA del centro: catálogo de arranque.

Estos son los productos que el cliente ve en la pestaña **Tienda** de su portal
y en la página pública de enlaces. Van sembrados para que la tienda no nazca
vacía; el coach los edita, desactiva o sustituye desde **Tienda → Productos**
(y ahí sube sus fotos y sus enlaces de compra reales).

⚠️ Los enlaces apuntan a la web del centro: cuando exista la tienda online
definitiva, basta con cambiar `url` (o hacerlo desde la web, sin tocar código).
"""

from app import branding

_WEB = (branding.CONTACT_WEB or "https://professionalfitness.es").rstrip("/")

PRODUCTS: list[dict] = [
    {
        "title": "Proteína de suero",
        "description": "El complemento más rentable si te cuesta llegar a la "
                       "proteína del día. Un cacito tras entrenar o en la merienda.",
        "url": f"{_WEB}/tienda/proteina",
        "category": "suplemento",
        "sort_order": 10,
    },
    {
        "title": "Creatina monohidrato",
        "description": "3-5 g al día, todos los días. El suplemento con más "
                       "evidencia para fuerza y masa muscular.",
        "url": f"{_WEB}/tienda/creatina",
        "category": "suplemento",
        "sort_order": 20,
    },
    {
        "title": "Vitamina D3",
        "description": "Para quien entrena a cubierto y ve poco el sol. "
                       "Consúltalo con tu médico si tomas otra medicación.",
        "url": f"{_WEB}/tienda/vitamina-d",
        "category": "suplemento",
        "sort_order": 30,
    },
    {
        "title": "Bandas elásticas",
        "description": "Para calentar el hombro y el glúteo antes de entrenar, "
                       "y para entrenar fuera de casa sin excusas.",
        "url": f"{_WEB}/tienda/bandas",
        "category": "material",
        "sort_order": 40,
    },
    {
        "title": "Cinturón de lumbares",
        "description": "Para las series pesadas de sentadilla y peso muerto "
                       "cuando ya dominas la técnica.",
        "url": f"{_WEB}/tienda/cinturon",
        "category": "material",
        "sort_order": 50,
    },
    {
        "title": "Camiseta técnica del centro",
        "description": "La equipación del centro: tejido técnico y transpirable "
                       "para entrenar cómodo.",
        "url": f"{_WEB}/tienda/camiseta",
        "category": "otro",
        "sort_order": 60,
    },
    {
        "title": "Botella de 750 ml",
        "description": "Con marcas de medida: la forma más simple de saber si "
                       "llegas a los litros de agua del día.",
        "url": f"{_WEB}/tienda/botella",
        "category": "otro",
        "sort_order": 70,
    },
]
