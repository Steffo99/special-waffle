from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Column, BigInteger, Integer, String, ForeignKey, create_engine, func
from enum import IntEnum
import config

engine = create_engine(config.database)
Base = declarative_base(bind=engine)
Session = sessionmaker(bind=engine)

session = Session()

class Vote(IntEnum):
    QUIT = 1
    REVEAL = 2
    EXPAND = 3


class WaffleStatus(IntEnum):
    CHATTING = 1
    MATCHMAKING = 2


class User(Base):
    __tablename__ = "wusers"

    tid = Column(BigInteger, primary_key=True)
    tusername = Column(String)
    tfirstname = Column(String, nullable=False)
    tlastname = Column(String)

    waffle_id = Column(Integer, ForeignKey("waffle.id"))
    waffle = relationship("Waffle", back_populates="users")
    icon = Column(String)
    vote = Column(Integer)

    def __str__(self):
        if self.tusername is not None:
            return f"@{self.tusername}"
        elif self.tlastname is not None:
            return f"{self.tfirstname} {self.tlastname}"
        else:
            return f"{self.tfirstname}"

    def __repr__(self):
        return f"<User #{self.tid}>"

    async def message(self, bot, msg):
        await bot.sendMessage(self.tid, msg)

    def join_waffle(self, waffle_id):
        self.waffle_id = waffle_id
        # TODO: improve this
        self.icon = self.tfirstname[0]

    def leave_waffle(self):
        self.waffle_id = None
        self.icon = None
        self.vote = None


class Waffle(Base):
    __tablename__ = "waffle"

    id = Column(Integer, primary_key=True)
    users = relationship("User", back_populates="waffle")
    status = Column(Integer, nullable=False)

    def count_votes(self):
        vquit, vreveal, vexpand = 0, 0, 0
        for user in self.users:
            if user.vote == Vote.QUIT:
                vquit += 1
            elif user.vote == Vote.REVEAL:
                vreveal += 1
            elif user.vote == Vote.EXPAND:
                vexpand += 1
        return vquit, vreveal, vexpand

    async def message(self, bot, msg):
        for user in self.users:
            await user.message(bot, msg)

if __name__ == "__main__":
    Base.metadata.create_all()