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


    def get_cut_labels(self, category):
        labels = self._f["cut_labels"]
        return [*labels["skim"], *labels["preselection"], *labels[category]]


    def get_cutflow(self, category, sample, years=None):
        all_datasets = list(self._f["cutflow_cumulative"]["initial"].keys())
        if years is not None:
            dataset_keys = [dk for year in years for dk in all_datasets if year in dk]
        else:
            dataset_keys = all_datasets

        values = []

        initial = self._f["cutflow_cumulative"]["initial"]
        values.append(sum(initial[dk] for dk in dataset_keys))

        skim = self._f["cutflow_cumulative"]["skim"]
        for cut_name in skim:
            values.append(sum(skim[cut_name][dk] for dk in dataset_keys))

        presel = self._f["cutflow_cumulative"]["preselection"]
        for cut_name in presel:
            values.append(sum(presel[cut_name][dk]["nominal"] for dk in dataset_keys))

        cat = self._f["cutflow_cumulative"][category]
        for cut_name in cat:
            values.append(sum(cat[cut_name][dk][sample]["nominal"] for dk in dataset_keys))

        return values


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


