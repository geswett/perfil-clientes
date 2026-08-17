"""Esquema del Perfil de Cargo (levantamiento con cliente).

Este esquema replica la estructura del formato usado por Puelche Human
Consulting para el levantamiento de perfiles de cargo con clientes:

  I.   Datos Generales Empresa
  II.  Organigrama
  III. Descripción del Cargo
  IV.  Requisitos para el Cargo
  V.   Perfil Candidato
  VI.  Competencias
  VII. Condiciones Laborales

Se usa como `response_schema` al pedirle a Gemini que estructure la
transcripción (de audio, de foto o texto escrito) en estos campos, y
también como estructura de datos para generar el .docx final.
"""

from pydantic import BaseModel, Field
from typing import List


# Filas fijas de la sección IV (Requisitos para el Cargo). Cada fila tiene
# columna "Excluyente" (obligatorio) y "Deseable" (nice-to-have).
REQUISITOS_FILAS = [
    "Formación",
    "Experiencia",
    "Experiencia en la industria",
    "Competencias Técnicas",
    "Licencia",
    "Idioma",
]


class DatosGeneralesEmpresa(BaseModel):
    definicion_empresa: str = Field(
        description="Breve descripción de la empresa: rubro, tamaño, cobertura, trayectoria."
    )
    situacion_actual: str = Field(
        description="Contexto y motivo de la búsqueda: por qué se abre o crea este cargo ahora."
    )
    area_de_la_que_depende: str = Field(
        description="Gerencia o área a la que pertenece el cargo."
    )
    plazo_deseado_ingreso: str = Field(
        description="Plazo en el que el cliente espera que la persona seleccionada ingrese. 'Por definir' si no se menciona."
    )
    opciones_crecimiento: str = Field(
        description="Proyección de carrera / crecimiento futuro del cargo, si se menciona."
    )
    confidencialidad_cargo: str = Field(
        description="Si el proceso es confidencial o abierto. 'Por definir' si no se menciona."
    )


class Organigrama(BaseModel):
    jefatura_directa: str = Field(
        description="Nombre y cargo de la jefatura directa a quien reporta la posición."
    )
    reporta_indirectamente: str = Field(
        description="A quién reporta indirectamente, si aplica. 'No aplica' si no se menciona."
    )
    personas_a_cargo: str = Field(
        description="Cantidad y tipo de personas a cargo directas, o liderazgo funcional/transversal."
    )
    tamano_empresa: str = Field(
        description="Tamaño de la empresa: dotación, facturación, sucursales, líneas de negocio, si se mencionan."
    )


class DescripcionCargo(BaseModel):
    nombre_cargo: str = Field(description="Nombre / título del cargo a buscar.")
    proposito_cargo: str = Field(
        description="Propósito general del cargo: su rol y aporte a la cadena de valor de la empresa."
    )
    funciones_cargo: List[str] = Field(
        description="Lista de funciones principales del cargo, redactadas como acciones (verbo en infinitivo al inicio de cada una)."
    )


class RequisitoFila(BaseModel):
    requerimiento: str = Field(
        description="Nombre de la fila, por ejemplo 'Formación', 'Experiencia', 'Experiencia en la industria', 'Competencias Técnicas', 'Licencia' o 'Idioma'."
    )
    excluyente: str = Field(
        description="Requisito obligatorio/excluyente para esa fila. 'No requerido' si no aplica."
    )
    deseable: str = Field(
        description="Requisito deseable pero no obligatorio para esa fila. 'No requerido' si no aplica."
    )


class Competencia(BaseModel):
    competencia: str = Field(description="Nombre corto de la competencia.")
    definicion: str = Field(description="Definición de en qué consiste esa competencia para este cargo.")


class CondicionesLaborales(BaseModel):
    ubicacion: str = Field(description="Ciudad / lugar de trabajo.")
    jornada_laboral: str = Field(description="Días y horario de trabajo. 'Por definir' si no se menciona.")
    renta: str = Field(description="Renta ofrecida (líquida o bruta, según se mencione). 'Por definir' si no se menciona.")
    beneficios: str = Field(description="Beneficios ofrecidos por la empresa. 'Por confirmar' si no se menciona.")
    tipo_contrato: str = Field(description="Tipo de contrato (plazo fijo, indefinido, honorarios, etc.).")


class PerfilCargo(BaseModel):
    """Estructura completa del Perfil de Cargo levantado en la reunión con el cliente."""

    empresa: DatosGeneralesEmpresa
    organigrama: Organigrama
    descripcion_cargo: DescripcionCargo
    requisitos: List[RequisitoFila] = Field(
        description="Debe contener exactamente estas 6 filas, en este orden: Formación, Experiencia, "
        "Experiencia en la industria, Competencias Técnicas, Licencia, Idioma."
    )
    perfil_candidato: str = Field(
        description="Características específicas que debe tener el/la candidato/a ideal: rasgos, forma de trabajo, "
        "lo que NO se busca, etc."
    )
    competencias: List[Competencia] = Field(
        description="Entre 5 y 9 competencias clave para el cargo, cada una con su definición aplicada al contexto del cargo."
    )
    condiciones_laborales: CondicionesLaborales
