from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean

import db


class Ruleta(db.Base):
    """Representa una tirada de ruleta registrada por OCR."""

    __tablename__ = "ruleta"

    id = Column(Integer, primary_key=True)
    numero = Column(Integer, nullable=False)
    mayor = Column(String, nullable=False)
    menor = Column(String, nullable=False)
    par = Column(Boolean, nullable=False)
    impar = Column(Boolean, nullable=False)
    fecha = Column(DateTime, nullable=False)

    def __init__(self, numero, mayor, menor, par, impar, fecha=None):
        self.numero = numero
        self.mayor = mayor
        self.menor = menor
        self.par = par
        self.impar = impar
        self.fecha = fecha or datetime.now()

    def __repr__(self):
        grupo = self.mayor if self.numero > 18 else self.menor
        paridad = self.par if self.numero % 2 == 0 else self.impar
        return "Datos de la tirada: Numero: {}| {}| {}| {}".format(
            self.numero, grupo, paridad, self.fecha
        )

    # Se reutiliza __repr__ en lugar de duplicar la misma lógica dos veces.
    __str__ = __repr__
