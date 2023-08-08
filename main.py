from obg.core import statistics, tree, protocols, api, evaluation, validators, operations

from obg.utils.files import get_data, get_options, options_from_data, reformat_data, dump_reformated_data
from obg.utils.logging import logger
import sys

from obg.core.statistics import clash_count

data = statistics.to_dict_uuid(get_data(), predicate=statistics.clean(lambda x: x[:5]))
# options = statistics.to_list(get_options(), predicate=lambda x: x[1])
options = options_from_data(data)
# data, options = reformat_data(data)

# dump_reformated_data(new_data, options)

# print(options)
# # cache = Cache(data, get_options())

# popularity = statistics.subject_popularity(data, options)
# classes = statistics.calculate_classes(popularity, class_size=24)
# filtered = statistics.filter_grouped_by(classes, 2)
# print(filtered)

from time import perf_counter


def run(*args):
    gen = api.Generator(
        data, 
        options, 
        number_of_blocks=4, 
        class_size=25,
        protocol=protocols.Protocol(),
        validators=[
            validators.MaxSubjectsValidator(max_value=12)
        ]
    )

    gen.setup()
    gen.define_ebacc(
        humanities=["Hi", "Ge"],
        science=["Sc"],
        languages=["Fr"],
        vocational=["Bb"]
    )
    
    
    gen.run_with_threshold(max_students=20)
    
    best = gen.evaluate()
    best.calculate_students()
    best.pprint()
    
    return gen.best_evaluation.blocks

if __name__ == "__main__":
    run()
