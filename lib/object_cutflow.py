import awkward as ak


class ObjectCutflow:
    def __init__(self, collection, cuts):
        self.collection = collection
        self.cuts = cuts
        self._object_masks = []


    def run(self, events, processor_params, **kwargs):
        cumul = ak.ones_like(events[self.collection].pt, dtype=bool)
        self._object_masks = []

        for cut in self.cuts:
            cumul = cumul & cut.get_mask(events, processor_params, **kwargs)
            self._object_masks.append(cumul)


    def get_object_mask(self, i):
        return self._object_masks[i]


    def get_event_mask(self, i):
        return ak.any(self._object_masks[i], axis=1)


    def get_event_count(self, i):
        return int(ak.sum(self.get_event_mask(i)))


    def get_final_object_mask(self):
        return self._object_masks[-1]


    def get_final_event_mask(self):
        return self.get_event_mask(-1)


    def __len__(self):
        return len(self.cuts)
