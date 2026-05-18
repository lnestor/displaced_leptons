import coffea.util

class CoffeaFile:
    def __init__(self, filename):
        self.filename = filename
        self._f = coffea.util.load(filename)


    def get_total_hist(self, hist_name, samples=None, years=None, category=None):
        hists = []

        samples = samples if samples is not None else self.get_samples(hist_name)

        year_keys = self._get_year_keys(hist_name, samples)
        if years is not None:
            year_keys = [yk for year in years for yk in year_keys if year in yk]

        category = category if category is not None else "baseline"

        for sample in samples:
            for yk in year_keys:
                hists.append(self.get_hist(hist_name, sample, yk, category))

        return sum(hists)


    def get_hist(self, hist_name, sample, year_key, category):
        h = self._f["variables"][hist_name][sample][year_key]
        return h[category, ...]


    def hist_names(self):
        return list(self._f["variables"].keys())


    def get_samples(self, hist_name):
        return list(self._f["variables"][hist_name].keys())


    def get_years(self, hist_name, sample):
        return [self._extract_year(yk) for yk in self._get_year_keys(hist_name, sample)]


    def _get_year_keys(self, hist_name, samples):
        if isinstance(samples, str):
            samples = [samples]

        keys = set()
        for sample in samples:
            keys.update(self._f["variables"][hist_name][sample].keys())

        return list(keys)

    def _extract_year(self, year_key):
        return year_key.split("_")[1]


    def _expand_hist_names(self, hist_name_arg):
        if isinstance(hist_name_arg, list):
            pass
        elif isinstance(hist_name_arg, str):
            pass
        else:
            pass


