EdgeIdentifier = int | str
CoverageMap = dict[EdgeIdentifier, int]
TrialIdentifier = int | str
FuzzerMap = dict[TrialIdentifier, CoverageMap]
FuzzerIdentifier = int | str
CampaignMap = dict[FuzzerIdentifier, FuzzerMap]
