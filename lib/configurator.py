import pocket_coffea.utils.configurator as config

class Configurator(config.Configurator):
    def __init__(
        self,
        workflow,
        parameters,
        datasets,
        skim,
        object_selections
        event_preselections,
        categories,
        weights,
        variations,
        variables,
        weights_classes=None,
        calibrators=None,
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
            variables=variables,
            weights_classes=weights_classes,
            calibrators=calibrators,
            workflow_options=workflow_options,
            save_skimmed_files=save_skimmed_files,
            do_postprocessing=do_postprocessing
        )

        self.object_selections = object_selections

