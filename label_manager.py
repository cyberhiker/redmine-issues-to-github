#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

# +--------------------------------------------------+
# | Copyright (c) AD ticket GmbH                     |
# | All rights reserved.                             |
# +--------------------------------------------------+
# | AD ticket GmbH                                   |
# | Kaiserstraße 69                                  |
# | D-60329 Frankfurt am Main                        |
# |                                                  |
# | phone: +49 (0)69 407 662 0                       |
# | fax:   +49 (0)69 407 662 50                      |
# | mail:  github@adticket.de                        |
# | web:   www.ADticket.de                           |
# +--------------------------------------------------+
# | This library is free software: you can           |
# | redistribute it and/or modify it under the terms |
# | of the GNU General Public License as published   |
# | by the Free Software Foundation, either version  |
# | 3 of the License, or (at your option) any later  |
# | version.                                         |
# |                                                  |
# | In addition you are required to retain all       |
# | author attributions provided in this software    |
# | and attribute all modifications made by you      |
# | clearly and in an appropriate way.               |
# |                                                  |
# | This software is distributed in the hope that    |
# | it will be useful, but WITHOUT ANY WARRANTY;     |
# | without even the implied warranty of             |
# | MERCHANTABILITY or FITNESS FOR A PARTICULAR      |
# | PURPOSE.  See the GNU General Public License for |
# | more details.                                    |
# |                                                  |
# | You should have received a copy of the GNU       |
# | General Public License along with this software. |
# | If not, see <http://www.gnu.org/licenses/>.      |
# +--------------------------------------------------+

'''A little helper to recolor labels

@see http://develop.github.com/

@author Markus Tacker <m@coderbyheart.de>'''

import io
import sys
import os
import urllib.request
import urllib.parse
import json
from base64 import encodebytes as base64

class LabelManager(object):
    
    def __init__(self, user, repo, authUser, authPassword):       
        self.baseurl = "https://api.github.com/repos/%s/%s/" % (user, repo)
        self.authData = base64(bytes(('%s:%s' % (authUser, authPassword)), 'utf-8')).decode().replace('\n', '')
        self.fetchLabels()
        
    def fetchLabels(self):
        'Fetch label data'
        self.labels = []
        labelsUrl = self.baseurl + "labels"
        req = urllib.request.Request(labelsUrl)
        req.add_header('Authorization', 'Basic %s' % self.authData)
        res = urllib.request.urlopen(req)
        for label in json.loads(res.read().decode('utf-8')):
            self.labels.append(label)
            
    def saveLabels(self, outfile):
        'Save label and their colors to outfile'
        f = io.open(outfile, 'w+')
        for label in self.labels:
            f.write("%s: %s\n" % (label['name'], label['color']))
        f.close()
        
    def updateLabels(self, infile):
        'Update the label colors from infile'
        f = io.open(infile, 'r')
        for line in f.readlines():
            line = line.strip()
            if line:
                if line[0] == "#":
                    continue
                name, color = line.split(":")
                name = name.strip()
                color = color.strip().lower()
                labeldata = {
                    'name': name,
                    'color': color
                }
                print(labeldata)
                data = json.dumps(labeldata)
                clen = len(data)
                data = data.encode('utf-8')
                labelUrl = self.baseurl + "labels/" + name
                req = urllib.request.Request(labelUrl)
                req.add_header('Content-Type', 'application/json')
                req.add_header('Content-Length', str(clen))
                req.add_header('Authorization', 'Basic %s' % self.authData)
                try:
                    res = urllib.request.urlopen(req, data)
                except urllib.error.HTTPError as e:
                    print(e.msg)
                    print(e.fp.read().decode('utf-8'))
                    raise e
        f.close()

if __name__ == '__main__':
    user = 'github-user'
    repo = 'github-repo'
    authUser = 'your-github-username'
    authPassword = 'your-github-password'

    lm = LabelManager(user, repo, authUser, authPassword)
    # Write labels to a file
    # lm.saveLabels("labels.txt")
    # Read new colors from modified file
    # lm.updateLabels("new-labels.txt")
