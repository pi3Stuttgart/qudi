# -*- coding: utf-8 -*-

import os
from serial import Serial, EIGHTBITS,STOPBITS_ONE,PARITY_NONE
from core.configoption import ConfigOption
from core.module import Base

class ThorlabsElloFlipper(Base):
	_port = ConfigOption('port')
	def __init__(self, config, **kwargs):
		super().__init__(config=config, **kwargs)
		

	def disconnect(self):
		self.ell.close()
        
	def on_deactivate(self):
		self.disconnect()

	def on_activate(self):
		self.ell = Serial('COM5', baudrate=9600, bytesize=EIGHTBITS, stopbits=STOPBITS_ONE,parity= PARITY_NONE, timeout=2)
	def move_forward(self):
		self.ell.write(bytes(f"{self._port}fw", 'ascii'))

	def get_info(self):
		self.ell.write(bytes(f"{self._port}in", 'ascii'))
		return self.ell.read(5)

	def move_pos_1(self):
		self.ell.write(bytes("0ma00000000", 'ascii'))
	def move_pos_2(self):
		self.ell.write(bytes("0ma00000020", 'ascii'))
	def move_pos_3(self):
		self.ell.write(bytes("0ma00000040", 'ascii'))
	def move_pos_4(self):
		self.ell.write(bytes("0ma00000060", 'ascii'))

	def get_pos(self):
		""" Returns the current position of the stage. In degree angle
		"""
		self.ell.write(bytes(f"{self._port}gp", 'ascii'))
		pos16 = self.ell.read(32)
		pos10 = int("".join(filter(lambda x: x not in "brn\\'", str(pos16)))[3:], 16)
		return 1 if pos10 > 0 else 0
	def home(self):
		""" Homes the rotation mount.
		"""
		self.ell.write(bytes(f"{self._port}ho0", 'ascii'))
