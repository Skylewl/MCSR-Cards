import json

class Card:
    def __init__(self, name, uuid, image, pb, nea, fsa, ssa, fpa, sea, eea, fa):
        self.name = name
        self.uuid = uuid
        self.image = image
        self.pb = pb
        self.nea = nea
        self.fsa = fsa
        self.ssa = ssa
        self.fpa = fpa
        self.sea = sea 
        self.eea = eea 
        self.fa = fa
        print(f'before: {pb}')
        pb_calc = 1100 / 0.5 if pb is None else pb # default values if stats not found
        nea = 500 if nea is None else nea
        fsa = 600 / 0.71 if fsa is None else fsa
        ssa = 600 / 0.31 if ssa is None else ssa
        fpa = 700 / 0.235 if fpa is None else fpa
        sea = 800 / 0.19 if sea is None else sea
        eea = 900 / 0.18 if eea is None else eea
        fa = 1000 / 0.333 if fa is None else fa
        if pb is None:
            self.pb = 0    
        print(f'after: {pb}')
        scores_count = 0
        scores_sum = 0
        scores = [pb_calc*200, nea, fsa*6.2, ssa*16.8, fpa*24.6, sea*44.5, eea*79.1, fa*140]
        for i in scores:
            if i > 0:
                scores_sum += i
                scores_count += 1
        if scores_count > 0:
            scores_sum = scores_sum / scores_count
        else:
            scores_sum = 110000
        self.value = int((110000 - scores_sum) * 0.01)
        if self.value < 0:
            self.value = 0
        
    def to_dict(self):
        return {
            "name": self.name,
            "uuid": self.uuid,
            "image": self.image,
            "pb": self.pb,
            "nea": self.nea,
            "fsa": self.fsa,
            "ssa": self.ssa,
            "fpa": self.fpa,
            "sea": self.sea,
            "eea": self.eea,
            "fa": self.fa,
            "value": self.value
        }

    def to_json(self):
        return json.dumps(self.to_dict())
    



        