import os
import sys
import numpy as np
from bs4 import BeautifulSoup as bsoup
import openslide as ops
import matplotlib.pyplot as plt
import matplotlib.path as mplPath
import cv2

###################################
def usage(argv):
    print('Usage: %s {/path/to/BigTiff-Image-With-XML-Metainfo}' % os.path.basename(argv[0]))

###################################
class DataInfo:
    def __init__(self, pathImage):
        self.fnIMG=None
        self.fnXML=None
        self.fnMSK=None
        self.loadFromFileName(pathImage)
    def loadFromFileName(self, pathImage):
        if os.path.isfile(pathImage):
            tmpBn=os.path.splitext(pathImage)[0]
            tmpFnIMG='%s.tif' % tmpBn
            tmpFnXML='%s.xml' % tmpBn
            tmpFnMSK='%s_Mask.tif' % tmpBn
            self.checkIsFile(tmpFnIMG)
            self.checkIsFile(tmpFnXML)
            self.checkIsFile(tmpFnMSK)
            self.fnIMG=tmpFnIMG
            self.fnXML=tmpFnXML
            self.fnMSK=tmpFnMSK
            # self.dataXML=self.readXmlData(self.fnXML)
            self.readXmlData(self.fnXML)
            self.dataIMG=ops.OpenSlide(self.fnIMG)
        else:
            self.checkIsFile(pathImage)
            sys.exit(1)
    def isInitialized(self):
        return (self.fnIMG is not None)
    def checkIsFile(self, fnpath, isFinIfNotFound=True):
        if not os.path.isfile(fnpath):
            print('Cant find file [%s], exit...' % fnpath)
            if isFinIfNotFound:
                sys.exit(1)
    def toString(self):
        if not self.isInitialized():
            return 'XML-DataInfo: is not initialized'
        else:
            tstr='XML-DataInfo: '
            for kk,vv in self.dataXML.items():
                tstr += '[%s]:%d, ' % (kk, len(vv))
            return tstr
    def __str__(self):
        return self.toString()
    def __repr__(self):
        return self.toString()
    def readXmlData(self, fnXML, isCleanEmptyGroups=True, isDebug=False):
        with open(fnXML,'r') as f:
            # (1) read data
            dataXML=bsoup(f.read(),'lxml-xml')
            if isDebug:
                print(dataXML.prettify())
            dictGroup={}
            # (2) parse groups
            for ii in dataXML.findAll('Group'):
                tmp=dict(ii.attrs)
                dictGroup[tmp['Name']]=[]
            if isDebug:
                print dictGroup
            # (3) iterate coords
            for i,ii in enumerate(dataXML.findAll('Annotation')):
                tmp=dict(ii.attrs)
                tIdGroup=tmp['PartOfGroup']
                lstCoords=[]
                for j,jj in enumerate(ii.findAll('Coordinate')):
                    tx=np.float(jj.attrs['X'])
                    ty=np.float(jj.attrs['Y'])
                    tp=np.int(jj.attrs['Order'])
                    lstCoords.append((tp,tx,ty))
                    if isDebug and ((j%2000)==0):
                        print tIdGroup, '(',i,')[',j,'] : {', tp,tx,ty,'}'
                arrCoords=np.array(lstCoords)
                sidx=np.argsort(arrCoords[:,0])
                arrCoords=arrCoords[sidx,1:]
                arrCoords=np.append(arrCoords,[arrCoords[0]],axis=0)
                dictGroup[tIdGroup].append(arrCoords)
            # (4) Clean empty Groups:
            if isCleanEmptyGroups:
                tlstKeyEmpty=[kk for kk,vv in dictGroup.items() if len(vv)<1]
                if isDebug:
                    print 'Empty keys: ', tlstKeyEmpty
                for kk in tlstKeyEmpty:
                    del dictGroup[kk]
            # (5) Create plain MplPaths:
            self.lstGroupId=[]
            self.lstPaths=[]
            for kk,gg in enumerate(dictGroup.values()):
                for ii in gg:
                    self.lstGroupId.append(kk)
                    self.lstPaths.append(mplPath.Path(ii))
                print kk, ' : ', len(gg)
            #
            self.lstSubPaths=[]
            for ii in self.lstPaths:
                tmp=[]
                for j0,jj in enumerate(self.lstPaths):
                    if ii!=jj:
                        if ii.contains_path(jj):
                            tmp.append(j0)
                self.lstSubPaths.append(tmp)
            #
            print '------------------'
            for i,ii in enumerate(self.lstSubPaths):
                print i, ' : ', len(ii), ' : ', dictGroup.keys()[self.lstGroupId[i]]
            #
            self.dataXML = dictGroup
            # return dictGroup

###################################
if __name__=='__main__':
    if len(sys.argv)<2:
        usage(sys.argv)
        sys.exit(1)
    fnPath=sys.argv[1]
    dataInfo=DataInfo(fnPath)
    print '----'
    print dataInfo
    #
    siz0=dataInfo.dataIMG.level_dimensions[0]
    print siz0
    tplgn=np.array([[0,0],[0,siz0[1]],[siz0[0],siz0[1]],[siz0[0],0],[0,0]])
    #
    sizTile=512
    sizTile2=sizTile/2
    XX=range(4*sizTile,siz0[0]-4*sizTile,sizTile)
    YY=range(4*sizTile,siz0[1]-4*sizTile,sizTile)
    lstCoordsPc=np.array([(xx,yy) for xx in XX for yy in YY])
    lstCoordsP1=np.array([(xx-sizTile2,yy-sizTile2) for xx in XX for yy in YY])
    lstCoordsP2=np.array([(xx-sizTile2,yy+sizTile2) for xx in XX for yy in YY])
    lstCoordsP3=np.array([(xx+sizTile2,yy+sizTile2) for xx in XX for yy in YY])
    lstCoordsP4=np.array([(xx+sizTile2,yy-sizTile2) for xx in XX for yy in YY])
    lstPathTiles=[]
    for i,ii in enumerate(dataInfo.lstPaths):
        tmp=ii.contains_points(lstCoordsP1)&ii.contains_points(lstCoordsP2)&ii.contains_points(lstCoordsP3)&ii.contains_points(lstCoordsP4)
        tmp0=np.zeros(tmp.shape, dtype=np.bool)
        for jj in dataInfo.lstSubPaths[i]:
            tmpPath=dataInfo.lstPaths[jj]
            tmp0 |= tmpPath.contains_points(lstCoordsP1)|tmpPath.contains_points(lstCoordsP2)|tmpPath.contains_points(lstCoordsP3)|tmpPath.contains_points(lstCoordsP4)
            # tmp0 |= tmpPath.contains_points(lstCoordsP1)&tmpPath.contains_points(lstCoordsP2)&tmpPath.contains_points(lstCoordsP3)&tmpPath.contains_points(lstCoordsP4)
        tmp1=(tmp&(~tmp0))
        lstPathTiles.append(lstCoordsPc[tmp1,:])
        print '----'
    #
    plt.figure()
    plt.hold(True)
    plt.plot(tplgn[:,0],tplgn[:,1])
    for gg in dataInfo.dataXML.values():
        for ii in gg:
            plt.plot(ii[:,0],siz0[1]-ii[:,1])
    for ii in lstPathTiles:
        for pp in ii:
            tmp=np.array([(pp[0]-sizTile2,pp[1]-sizTile2),(pp[0]-sizTile2,pp[1]+sizTile2),(pp[0]+sizTile2,pp[1]+sizTile2),(pp[0]+sizTile2,pp[1]-sizTile2),(pp[0]-sizTile2,pp[1]-sizTile2)])
            plt.plot(tmp[:,0],siz0[1]-tmp[:,1])
    plt.hold(False)
    plt.grid(True)
    plt.show()

