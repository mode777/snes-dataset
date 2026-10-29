"""Item pipelines — extend as needed (dedup, validation, normalization)."""


class SnesDatasetPipeline:
    def process_item(self, item, spider):
        return item
