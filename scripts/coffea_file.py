import coffea.util
import hist

class CoffeaFile:
    def __init__(self, filename):
        self.filename = filename
        self._f = coffea.util.load(filename)


    def get_total_hist(self, hist_name, samples=None, years=None, category=None):
        hists = []

        samples = samples if samples is not None else self.get_samples(hist_name)

        year_keys = self._get_year_keys(hist_name, samples)
        if years is not None:
            year_keys = [yk for yk in year_keys if self._dataset_year(yk) in years]

        category = category if category is not None else "baseline"

        for sample in samples:
            for yk in year_keys:
                hists.append(self.get_hist(hist_name, sample, yk, category))

        return sum(hists)


    def get_hist(self, hist_name, sample, year_key, category):
        h = self._f["variables"][hist_name][sample][year_key]
        h = h[category, ...]
        if h.ndim > 1 and isinstance(h.axes[0], hist.axis.StrCategory):
            h = h["nominal", ...]
        return h


    def hist_names(self):
        return list(self._f["variables"].keys())


    def get_samples(self, hist_name):
        return list(self._f["variables"][hist_name].keys())


    def get_years(self, hist_name, sample):
        return list(set(self._dataset_year(yk) for yk in self._get_year_keys(hist_name, sample)))


    def get_categories(self, hist_name):
        sample = self.get_samples(hist_name)[0]
        dataset = self._get_year_keys(hist_name, [sample])[0]
        ax = self._f["variables"][hist_name][sample][dataset].axes[0]
        return [ax.value(i) for i in range(ax.extent - 1)]


    def is_data(self, sample, hist_name):
        year_keys = self._get_year_keys(hist_name, [sample])
        return self._f["datasets_metadata"]["by_dataset"][year_keys[0]]["isMC"] == "False"


    def get_cut_labels(self, category):
        labels = self._f["cut_labels"]
        obj_labels = list(labels.get("object_selection", []))
        return [*labels["skim"], *labels["preselection"], *obj_labels, *labels[category]]


    def get_cutflow(self, category, sample, years=None):
        all_datasets = list(self._f["cutflow_cumulative"]["initial"].keys())
        if years is not None:
            dataset_keys = [dk for dk in all_datasets if self._dataset_year(dk) in years]
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

        if "object_selection" in self._f["cutflow_cumulative"]:
            obj_sel = self._f["cutflow_cumulative"]["object_selection"]
            for cut_name in obj_sel:
                values.append(sum(obj_sel[cut_name][dk]["nominal"] for dk in dataset_keys))

        cat = self._f["cutflow_cumulative"][category]
        for cut_name in cat:
            if sample is None:
                values.append(sum(cat[cut_name][dk][s]["nominal"] for dk in dataset_keys for s in cat[cut_name][dk]))
            else:
                values.append(sum(cat[cut_name][dk][sample]["nominal"] for dk in dataset_keys))

        return values


    def _get_year_keys(self, hist_name, samples):
        if isinstance(samples, str):
            samples = [samples]

        keys = set()
        for sample in samples:
            keys.update(self._f["variables"][hist_name][sample].keys())

        return list(keys)


    def _dataset_year(self, dataset):
        return self._f["datasets_metadata"]["by_dataset"][dataset]["year"]


    def _expand_hist_names(self, hist_name_arg):
        if isinstance(hist_name_arg, list):
            pass
        elif isinstance(hist_name_arg, str):
            pass
        else:
            pass


