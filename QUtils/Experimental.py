"""
# ==Construction Site== #\n
##  =- under construction -=\n
**Please Keep Back From The Barrier**\n
*Heavy Duty Vehicles In Use*
"""

__author__ = "Roxanne Minerals"
__version__ = 1.0

from .Processing import *

class VectorProcessing_Experimental(VectorProcessing):

    @QUtilsExceptions.ErrorHandling
    def longestPath(self, startingcoord: QgsPointXY, printfeedback = True):
        clone = self.Features()
        clone.setFeatureIdReturn(True)
        clone.startEditing()
        clone.dataProvider().addAttributes(NewFields(("OLD_SELF", FieldType.array)))
        clone.updateFields()
        clone.commitChanges()
        startingfeature: QgsFeature = next(clone.newCursor(QgsFeatureRequest().setDistanceWithin(QgsGeometry.fromPointXY(startingcoord), 0.5)), None)
        if startingfeature is None:
            QUtilsExceptions.CriticalError(f"Coordinate {startingcoord} is not on a feature. You missed...", self.feedback)

        feedback = self.feedback
        stepsfeedback = self.feedback
        stepsfeedback = QgsProcessingFeedback()
        if not printfeedback:
            feedback = QgsProcessingFeedback()
            stepsfeedback = QgsProcessingFeedback()

        thingy = [0]

        def traverse(feature: QgsFeature, startingcoord: QgsPointXY, local_skip: list = None, old_self: list = None, start = False) -> tuple[float, list[QgsFeature]]:
            feedback.pushInfo(f"new traversal: {feature.id()}")
            feedback.pushInfo(f"feature length: {feature.geometry().length()}")
            feedback.pushInfo(f"startingcood: {startingcoord}")

            if feature.id() in recursionTrap.keys():
                recursionTrap[feature.id()] += 1
                if recursionTrap[feature.id()] == 10:
                    raise RecursionError()
            else:
                recursionTrap[feature.id()] = 1

            if local_skip is None:
                local_skip = []
            if old_self is None:
                old_self = []

            if "OLD_SELF" not in feature.fields().names():
                feature.setFields(NewFields(("OLD_SELF", FieldType.array), feature.fields()), False)
            selves: list = feature["OLD_SELF"]
            if not isinstance(selves, list):
                selves = []
            selves.append(feature.id())
            attr: list = feature.attributes()
            #feedback.pushInfo(f"attr: {attr}, fields: {feature.fields().names()}")
            attr.pop(len(feature.fields()) - 1)
            attr.append(selves)
            clone.startEditing()
            feature.setAttributes(attr)
            clone.changeAttributeValuesV2(clone.featureIdToLayerFid(feature.id()), attr)
            clone.commitChanges()
            _old_self: list = feature["OLD_SELF"]
            _local_skip = local_skip.copy()

            feedback.pushInfo(f"local skip: {local_skip}")
            feedback.pushInfo(f"old self of locator: {old_self}, old self: {feature['OLD_SELF']}")

            geometry = feature.geometry()
            geometry.convertToSingleType()
            geomlength = geometry.length()
            polyline: list[QgsPointXY] = geometry.asPolyline()
            steplength = geomlength
            if int(geomlength) > 0:
                steplength = ((geomlength - int(geomlength)) / int(geomlength)) + 1
            steps = int(geomlength / steplength)
            calculated_length = steplength * steps
            steps += int(geomlength) - int(calculated_length)
            feedback.pushInfo(f"calculated length: {calculated_length}")

            startingvertex = geometry.closestVertex(startingcoord)[1]
            feedback.pushInfo(f"starting vertex: {startingvertex}, {geometry.vertexAt(startingvertex)}")
            feedback.pushInfo(f"steps {steps}, step length {steplength}")

            _range = range(0, steps + 1)
            reverse = False
            if startingvertex == len(polyline) - 1:
                reverse = True
                _range = range(-steps, 1)

            attrs: list = feature.attributes()
            if geometry.vertexAt(0).distance(startingcoord.x(), startingcoord.y()) > steplength / 2 and geometry.vertexAt(len(polyline) - 1).distance(startingcoord.x(), startingcoord.y()) > steplength / 2:
                feedback.pushInfo("Middle Split!!!")
                splitfeature1 = QgsFeature()
                splitfeature1.setId(max(clone.allFids()) + 1)
                splitfeature1.setFields(feature.fields())
                attrs.pop(0)
                attrs.insert(0, splitfeature1.id())
                splitfeature1.setAttributes(attrs)
                splitfeature2 = QgsFeature()
                splitfeature2.setId(max(clone.allFids()) + 2)
                splitfeature2.setFields(feature.fields())
                attrs.pop(0)
                attrs.insert(0, splitfeature2.id())
                splitfeature2.setAttributes(attrs)
                feedback.pushInfo(f"1: {splitfeature1.id()}, 2: {splitfeature2.id()}")

                _clostestvertex = geometry.closestVertex(startingcoord)[0]
                _posangle = geometry.angleAtVertex(geometry.closestVertex(startingcoord)[1]) + 90
                if _clostestvertex != startingcoord:
                    feedback.pushInfo("Azemuth!")
                    _posangle = math.radians(_clostestvertex.azimuth(startingcoord))
                _pos1 = QgsPointXY(startingcoord.x() + (0.1 * math.cos(_posangle)), startingcoord.y() - (0.1 * math.sin(_posangle)))
                _pos2 = QgsPointXY(startingcoord.x() - (0.1 * math.cos(_posangle)), startingcoord.y() + (0.1 * math.sin(_posangle)))
                feedback.pushInfo(f"_splitgeom: {feature.geometry().splitGeometry([_pos1, _pos2], False)}, pos1: {_pos1}, pos2: {_pos2}")
                _splitgeom: QgsGeometry = geometry.splitGeometry([_pos1, _pos2], False)[1][0]
                splitfeature1.setGeometry(_splitgeom)

                splitline2 = []
                for point in polyline:
                    if not _splitgeom.contains(point) and not (_splitgeom.vertexAt(0).x() == point.x() and _splitgeom.vertexAt(0).y() == point.y()) and not (_splitgeom.vertexAt(len(_splitgeom.asPolyline()) - 1).x() == point.x() and _splitgeom.vertexAt(len(_splitgeom.asPolyline()) - 1).y() == point.y()):
                        splitline2.append(point)
                splitline2.append(startingcoord)
                splitgeom2 = QgsGeometry.fromPolylineXY(splitline2)
                splitfeature2.setGeometry(splitgeom2)

                if feature.id() in clone and len(set(feature["OLD_SELF"])) > 1:
                    del clone[feature.id()]
                skip.append(feature.id())
                clone.addFeatures([splitfeature1, splitfeature2])
                #skip.append([splitfeature1.geometry().asPolyline(), splitfeature2.geometry().asPolyline()])
                #_local_skip.extend([splitfeature1.geometry().asPolyline(), splitfeature2.geometry().asPolyline()])
                _local_skip.extend([splitfeature1.id(), splitfeature2.id(), feature.id(), startingcoord])
                #_old_self.append(feature.id())
                
                tributary1 = traverse(splitfeature1, startingcoord, _local_skip, old_self)
                tributary2 = traverse(splitfeature2, startingcoord, _local_skip, old_self)
                if tributary1[0] > tributary2[0]:
                    return tributary1
                return tributary2


            featurelist = []
            longer = [0, []]
            endfeature = False
            step_n = 0
            for step in _range:
                step = abs(step)
                if self.feedback.isCanceled(): raise QgsProcessingException("Cancelled")
                stepsfeedback.pushInfo(f"step{step_n}") if str(step_n).endswith("00") else None
                if step_n == 0 and not start:
                    step_n += 1
                    continue
                pos = geometry.interpolate(steplength * step).asPoint()
                def check_pos():
                    feats = [feat for feat in clone.newCursor(QgsFeatureRequest().setDistanceWithin(QgsGeometry.fromPointXY(pos), steplength / 2)) if feat.id() not in _old_self and feat.id() not in old_self and not feat.geometry().asPolyline() == polyline]
                    #if feats: feedback.pushInfo(f"before found feats: {[feat.id() for feat in feats]}")
                    _f = []
                    for _feat in feats:
                        if _feat["OLD_SELF"] is None:
                            _feat[_feat.fields().indexFromName("OLD_SELF")] = [_feat.id()]
                        _f.append(_feat)
                    feats: list[QgsFeature] = _f
                    _feats = feats.copy()
                    do_split = False
                    remove_list = []
                    skip_pos: list[QgsPointXY] = [_pos for _pos in local_skip if isinstance(_pos, QgsPointXY)]
                    for _skip_pos in skip_pos:
                        if QgsGeometry.fromPointXY(_skip_pos).distance(QgsGeometry.fromPointXY(pos)) <= steplength / 2:
                            feedback.pushInfo(f"skip pos: {_skip_pos}")
                            return 0, [], True
                    for i, feat in enumerate(feats):
                        if feat["OLD_SELF"][0] == feature["OLD_SELF"][0]:
                            _feats.remove(feat)
                        elif feat.id() in skip:
                            #feedback.pushInfo(f"SKIP! {feat.id()}")
                            #feedback.pushInfo(f"feats: {feats}")
                            #feedback.pushInfo(f"_feats: {[(_feat.id(), _feat["OLD_SELF"]) for _feat in feats]}")
                            if [_feat.id() for _feat in feats if feat.id() in _feat["OLD_SELF"] and _feat.id() != feat.id()]:
                                feedback.pushInfo(f"skip remove: {feat.id()}")
                                _feats.remove(feat)
                                for _skip_pos in skip_pos:
                                    if QgsGeometry.fromPointXY(_skip_pos).distance(QgsGeometry.fromPointXY(pos)) <= steplength / 2 and feat.id() in local_skip:
                                        remove_list.append(feat)
                                if geometry.vertexAt(0).distance(pos.x(), pos.y()) > steplength / 2 and geometry.vertexAt(len(polyline) - 1).distance(pos.x(), pos.y()) > steplength / 2:
                                    do_split = True
                        elif feat.id() in local_skip and False:
                            feedback.pushInfo(f"Local Skip! {feat.id()}")
                            for _skip_pos in skip_pos:
                                if QgsGeometry.fromPointXY(_skip_pos).distance(QgsGeometry.fromPointXY(pos)) <= steplength / 2:
                                    _feats.remove(feat)
                                    remove_list.append(feat)
                                    feedback.pushInfo(f"1remove: {feat.id()}")
                                    do_split = True
                                    break
                    for feat in feats:
                        if [_feat.id() for _feat in remove_list if feat["OLD_SELF"][0] in _feat["OLD_SELF"] and _feat.id() != feat.id()] and feat.id() not in local_skip and feat in _feats:
                            feedback.pushInfo(f"oldself skip remove: {feat.id()}")
                            _feats.remove(feat)
                            remove_list.append(feat)
                            #if feat.geometry().vertexAt(0).distance(pos.x(), pos.y()) > 1 and feat.geometry().vertexAt(len(feat.geometry().asPolyline()) - 1).distance(pos.x(), pos.y()) > 1:
                            #    do_split = True

                    return feats, _feats, do_split
                feats, _feats, do_split = check_pos()
                _feats: list[QgsFeature]

                if feats == 0:
                    return (0, [])

                if len(_feats) == 0 and do_split:
                    endfeature = True

                _feats.append(feature)
                if len(_feats) <= 1 and not do_split:
                    if step_n == steps:
                        endfeature = True
                        feedback.pushInfo(f"step: {step_n}, pos: {pos}")
                        feedback.pushInfo("endfeature!!!")
                        break
                    step_n += 1
                    continue
                feedback.pushInfo(f"step: {step_n}")
                feedback.pushInfo(f"Features Found: {[feat.id() for feat in _feats]}, at {pos}")

                feedback.pushInfo(f"do_split: {do_split}")

                if len(_feats) > 1:
                    feedback.pushInfo(f"over 1")
                    feats = _feats

                if step_n < steps and step_n > 0:
                    posfeats = [feat for feat in feats if feat.geometry().asPolyline() != polyline]
                    for _posfeat in posfeats:
                        if "OLD_SELF" in _posfeat.fields().names():
                            if feature["OLD_SELF"][0] not in _posfeat["OLD_SELF"]:
                                posfeat = _posfeat
                                break
                        else:
                            posfeat = _posfeat
                            break
                    feedback.pushInfo(f"posfeat: {posfeat.id()}")
                    if "OLD_SELF" in posfeat.fields().names():
                        posfeat = clone[posfeat["OLD_SELF"][0]]
                        feedback.pushInfo(f"posfeat oldself: {posfeat.id()}")
                    posgeom = clone[feature["OLD_SELF"][0]].geometry().intersection(posfeat.geometry())
                    if posgeom.isMultipart() or QgsWkbTypes().displayString(posgeom.wkbType()) in "LineString":
                        if QgsWkbTypes().displayString(posgeom.wkbType()) in "MultiLineString":
                            posgeom.convertToSingleType()
                            posparts = posgeom.asPolyline()
                        else:
                            posparts = posgeom.asMultiPoint()
                        dist = [geomlength]
                        #if do_split: dist = [geomlength, pos]
                        feedback.pushInfo(f"type: {QgsWkbTypes().displayString(posgeom.wkbType())}, {posparts}")
                        for point in posparts:
                            if pos.distance(point.x(), point.y()) < dist[0]:
                                feedback.pushInfo(f"distance: {pos.distance(point.x(), point.y())}!!!")
                                dist = [pos.distance(point.x(), point.y()), point]
                        pos = QgsPointXY(dist[1].x(), dist[1].y())
                    else:
                        pos = posgeom.asPoint()

                    _, _feats, do_split = check_pos()
                    if len(_feats) == 0:
                        step_n += 1
                        continue
                    _feats.append(feature)

                #skip.append(feature.geometry().asPolyline())
                feats = _feats
                _local_skip.extend([feat.id() for feat in feats])
                _local_skip.append(pos)

                #testing
                featsid = [feat.id() for feat in feats]
                if 304 in featsid and 268 in featsid and 303 in featsid and False:
                    thingy[0] += 1
                    if thingy[0] == 1:
                        _f_ = []
                        _f_.extend([feats[1], feats[0], feats[2]])
                        feats = _f_

                for feat in feats:
                    if self.feedback.isCanceled(): raise QgsProcessingException("Cancelled")
                    feedback.pushInfo(f"feat id: {feat.id()}")

                    featgeom = feat.geometry()
                    if featgeom.asPolyline() == polyline:
                        if step_n < steps and step_n > 0 and not (featgeom.vertexAt(len(featgeom.asPolyline()) - 1) == QgsPoint(pos.x(), pos.y()) or featgeom.vertexAt(0) == QgsPoint(pos.x(), pos.y())):
                            clostestvertex = geometry.closestVertex(pos)[0]
                            posangle = geometry.angleAtVertex(geometry.closestVertex(pos)[1]) + 90
                            if clostestvertex != pos:
                                posangle = math.radians(clostestvertex.azimuth(pos))
                            pos1 = QgsPointXY(pos.x() + (0.1 * math.cos(posangle)), pos.y() - (0.1 * math.sin(posangle)))
                            pos2 = QgsPointXY(pos.x() - (0.1 * math.cos(posangle)), pos.y() + (0.1 * math.sin(posangle)))
                            splitgeom: list[QgsGeometry] = geometry.splitGeometry([pos1, pos2], False)[1]
                            
                            splitline = []
                            for point in featgeom.asPolyline():
                                if not splitgeom[0].contains(point) and not (splitgeom[0].vertexAt(0).x() == point.x() and splitgeom[0].vertexAt(0).y() == point.y()) and not (splitgeom[0].vertexAt(len(splitgeom[0].asPolyline()) - 1).x() == point.x() and splitgeom[0].vertexAt(len(splitgeom[0].asPolyline()) - 1).y() == point.y()):
                                    splitline.append(point)
                            splitline.append(pos)
                            splitgeom.append(QgsGeometry.fromPolylineXY(splitline))
                            if reverse: splitgeom.reverse()

                            splitfeature_traversed = QgsFeature()
                            splitfeature_traversed.setId(max(clone.allFids()) + 1)
                            splitfeature_traversed.setFields(feat.fields())
                            attrs.pop(0)
                            attrs.insert(0, splitfeature_traversed.id())
                            splitfeature_traversed.setAttributes(attrs)
                            splitfeature_traversed.setGeometry(splitgeom[1])
                            splitfeature_next = QgsFeature()
                            splitfeature_next.setId(max(clone.allFids()) + 2)
                            splitfeature_next.setFields(feat.fields())
                            attrs.pop(0)
                            attrs.insert(0, splitfeature_next.id())
                            splitfeature_next.setAttributes(attrs)
                            splitfeature_next.setGeometry(splitgeom[0])

                            if feat.id() in clone and len(set(feature["OLD_SELF"])) > 1:
                                del clone[feat.id()]
                            skip.append(feat.id())
                            #skip.extend([splitfeature_traversed.geometry().asPolyline(), splitfeature_next.geometry().asPolyline()])
                            _local_skip.extend([splitfeature_traversed.id(), splitfeature_next.id()])
                            clone.addFeatures([splitfeature_next, splitfeature_traversed])
                            geomlength = splitfeature_traversed.geometry().length()

                            if not do_split:
                                _traverse = traverse(splitfeature_next, pos, _local_skip, _old_self)
                                if _traverse[0] > longer[0]:
                                    longer = _traverse
                            featurelist.append(splitfeature_traversed)

                        else:
                            if do_split and False:
                                return (geomlength, [feature])
                            featurelist.append(feat)
                        continue

                    tributary = traverse(feat, pos, _local_skip, _old_self)
                    if tributary[0] > longer[0]:
                        longer = tributary
                break

            if not endfeature:
                featurelist.extend(longer[1])
            elif not do_split:
                featurelist.append(feature)

            length = longer[0] + geomlength

            return (length, featurelist)


        recursionTrap = {}
        skip = []

        length, features = traverse(startingfeature, startingcoord, start=True)

        feedback.pushInfo(f"length: {length}")

        layer = self.newLayerObject(NewVectorLayer("LineString", self.context, "LongestPath").id())
        layer.startEditing()
        layer.setCrs(self.crs())
        layer.dataProvider().addAttributes(features[0].fields())
        layer.updateFields()
        layer.dataProvider().addFeatures(features)

        layer.commitChanges()

        return layer