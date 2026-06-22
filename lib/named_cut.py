from pocket_coffea.lib.cut_definition import Cut

class NamedCut(Cut):
    def __init__(self, cut, label):
        super().__init__(
            name=cut.name,
            params=cut.params,
            function=cut.function,
            collection=cut.collection,
        )
        self.label = label
