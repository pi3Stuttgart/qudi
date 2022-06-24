# coding=utf-8
from __future__ import print_function, absolute_import, division
__metaclass__ = type

import numpy as np
import collections

"""
Enter 2D or 3D vector v as dict. 
- Cartesian coordinate: {'x': , 'y': , 'z'}
- Spherical: {'rho':, 'azim': , 'elev': }
- Polar is [rho, azimuth], 
"""


class Coord():
    """
    Main method is coord()
    Usage example: vec_cart = Coord().coord({'x'})    
    
    Insert vec as cartesian or spherical vector with fields according to 
    variables in cart_coord or sph_coord. Fields can be omitted, e.g. vec = {'x': 1}
    dim can be 3 for 3D.
    """

    cart_coord = ['x', 'y', 'z']
    sph_coord = ['rho', 'azim', 'elev']

    def coord(self, vec, coord_type='cart'):
        """
        Insert coordinate vector like {'x': 1} or {'rho': 1, 'azim': 2, 'elev':3}. 
        Coordinate type is assumed according to variable names.
        This vector then will be outputted with coordinate system coord_type, 
        i.e. Coord().coord({'z':10}, coord_type = 'sph') = {'rho':10, 'elev': pi/2, 'azim':0}
        """
        self.check_validity(vec)
        self.complete(vec)
        if coord_type == 'cart':
            return self.cart
        elif coord_type == 'sph':
            return self.sph
        else:
            raise Exception("At the moment only 'sph' or 'cart' are allowed as coord_type")

    def coord_unit(self, vec, coord_type='cart'):
        sph = self.coord(vec, coord_type='sph')
        sph['rho'] = 1
        return self.coord(vec=sph, coord_type=coord_type)

    def check_validity(self, vec):
        if type(vec) not in [dict, collections.OrderedDict]:
            raise Exception('Error: ', type(vec), vec)
        if len(vec) > 3:
            raise Exception("No more than three coordinates are allowed!")
        if self.cart_coord[0] in vec or self.cart_coord[1] in vec or self.cart_coord[2] in vec:
            if self.sph_coord[0] in vec or self.sph_coord[1] in vec or self.sph_coord[2] in vec:
                raise Exception("Cartesian and spherical coordinates mixed!")
        for key in vec.keys():
            if not key in self.cart_coord + self.sph_coord:
                raise Exception("The axis " + str(key) + " is not allowed!")

    def complete(self, vec):
        if self.cart_coord[0] in vec or self.cart_coord[1] in vec or self.cart_coord[2] in vec:
            vec_compl = {'x': 0, 'y': 0, 'z': 0}
            for axis in self.cart_coord:
                if axis in vec:
                    vec_compl[axis] = vec[axis]
            self.cart = vec_compl
            self.sph = cart2sph(vec_compl)
        else:
            vec_compl = {'rho': 1, 'azim': 0, 'elev': 0}
            for axis in self.sph_coord:
                if axis in vec:
                    vec_compl[axis] = vec[axis]
            self.sph = vec_compl
            self.cart = sph2cart(vec_compl)

def sph2cart(*args):
    if type(args[0]) == dict:
        sph = args[0]
    elif len(args) == 3:
        sph = dict(rho=args[0], elev=args[1], azim=args[2])
    else:
        raise Exception('Error')
    x = sph['rho'] * np.cos(sph['elev']) * np.cos(sph['azim'])
    y = sph['rho'] * np.cos(sph['elev']) * np.sin(sph['azim'])
    z = sph['rho'] * np.sin(sph['elev'])
    if type(args[0]) == dict:
        return {'x': x, 'y': y, 'z': z}
    elif len(args) == 3:
        return x, y, z

def cart2sph(*args):
    if type(args[0]) == dict:
        cart = args[0]
    elif len(args) == 3:
        cart = dict(x=args[0], y=args[1], z=args[2])
    else:
        raise Exception('Error: {}'.format(args))
    rho = np.sqrt(cart['x'] ** 2 + cart['y'] ** 2 + cart['z'] ** 2)
    azim = np.arctan2(cart['y'], cart['x'])
    elev = np.arctan2(cart['z'], np.sqrt(cart['x'] ** 2 + cart['y'] ** 2))
    if type(args[0]) == dict:
        return {'rho': rho, 'azim': azim, 'elev': elev}
    elif len(args) == 3:
        return rho, elev, azim

if __name__ == '__main__':
    a = Coord()