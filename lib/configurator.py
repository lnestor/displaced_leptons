import pocket_coffea.utils.configurator as config
from pocket_coffea.lib.calibrators.common import ElectronsScaleCalibrator, MuonsCalibrator
from lib.d0_correction_calibrator import D0CorrectionCalibrator

DEFAULT_WEIGHTS = {
    "common": {
        "inclusive": [
            "genWeight",
            "lumi",
            "XS"
        ],
        "bycategory": {}
    },
    "bysample": {}
}

DEFAULT_VARIATIONS = {
    "weights": {
        "common": {
            "inclusive": [],
            "bycategory": {}
        },
        "bysample": {}
    }
}

DEFAULT_CALIBRATORS = [ElectronsScaleCalibrator, MuonsCalibrator, D0CorrectionCalibrator]


class Configurator(config.Configurator):
    def __init__(
        self,
        workflow,
        parameters,
        datasets,
        skim,
        object_selections,
        event_preselections,
        categories,
        hists,
        supplements=[],
        custom_fields={},
        weights=DEFAULT_WEIGHTS,
        variations=DEFAULT_VARIATIONS,
        weights_classes=None,
        calibrators=DEFAULT_CALIBRATORS,
        workflow_options=None,
        save_skimmed_files=None,
        do_postprocessing=True
    ):
        super().__init__(
            workflow=workflow,
            parameters=parameters,
            datasets=datasets,
            skim=skim,
            preselections=event_preselections,
            categories=categories,
            weights=weights,
            variations=variations,
            variables=hists,
            weights_classes=weights_classes,
            calibrators=calibrators,
            workflow_options=workflow_options,
            save_skimmed_files=save_skimmed_files,
            do_postprocessing=do_postprocessing
        )

        self.object_selections = object_selections
        self.custom_fields = custom_fields
        self.supplements = supplements

        # TODO: Validate dictionaries

    def load_datasets(self):
        super().load_datasets()

        priority = self.datasets_cfg.get("priority")
        if priority:
            rank = {sample: i for i, sample in enumerate(priority)}
            unranked = len(priority)
            self.filesets = dict(sorted(
                self.filesets.items(),
                key=lambda item: rank.get(item[1]["metadata"]["sample"], unranked)
            ))

