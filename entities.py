from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime

engine = create_engine('sqlite:///ocremix-fy.db')
Session = sessionmaker(bind=engine)

Base = declarative_base()


class Remix(Base):
    __tablename__ = 'remix'

    id = Column(Integer, primary_key=True)
    remix_name = Column(String)
    yt_url = Column(String)
    date_posted = Column(DateTime)
    game_id = Column(Integer, ForeignKey('game.id'))
    game = relationship("Game", backref="remix")

    def __init__(self, remix_name, yt_url, date_posted, game):
        self.remix_name = remix_name
        self.yt_url = yt_url
        self.date_posted = date_posted
        self.game = game
