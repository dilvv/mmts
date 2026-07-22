import os, sys
import yaml
with open('configuration.yaml') as config_file:
    config = yaml.safe_load(config_file)
os.environ['FRAMEWORK_PATH'] = config['framework_path']
sys.path.append(config['framework_path'])
from scripts.offsets_calculator import offsets_calculator
from scripts.make_accuracy_plot import make_accuracy_plot
from scripts.flatness_calculator import flatness_calculator
from utils.io_tool import write_to_csv
from utils.db_tool import write_to_database


def main(offsets_inputs:list, flatness_inputs:list, tag:str = 'NoTag') -> None:

    os.system('mkdir -p ' + os.getenv('FRAMEWORK_PATH') + '/out')

    qc_data = {}

    # Offset
    # ----------------------------------------------------------
    for modules, txtfile in offsets_inputs:
        qc_data.update( offsets_calculator(modules, txtfile) )

    offsets_list = []
    for module, qc in qc_data.items():

        offsets = [
                module,
                qc['center_offsets']['sensor'][0],
                qc['center_offsets']['sensor'][1],
                qc['center_offsets']['pcb'][0],
                qc['center_offsets']['pcb'][1],
                qc['angle_offsets']['sensor'],
                qc['angle_offsets']['pcb']
                ]

        make_accuracy_plot([offsets], os.getenv('FRAMEWORK_PATH') + '/out' )
        offsets_list.append(offsets)

    make_accuracy_plot(offsets_list, os.getenv('FRAMEWORK_PATH') + '/out')

    # Flatness and thickness
    # ----------------------------------------------------------
    for module, txtfiles in flatness_inputs:
        m = module.split("-")[0]
        qc_data[m].update( flatness_calculator(module, txtfiles[0], isVacuum=True)[m] )
        if txtfiles[1] != "":
            qc_data[m].update( flatness_calculator(module, txtfiles[1])[m] )

    write_to_csv(qc_data, os.getenv('FRAMEWORK_PATH') + f'/out/output_{tag}.csv')

    # Upload to database
    write_to_database(qc_data, config)

if __name__ == '__main__':


    offsets_inputs = [

        (["320MHF1WCNT0159-AT07-R", "320MHF1WCNT0160-AT07-L"], "M226M227.txt"),
#        (["320MHL1WCNT0149-AT03-R", "320MHL1WCNT0150-AT03-L"], "M216M217.txt"),
#        (["320MHR1WCNT0155-AT04-L", "320MHR1WCNT0156-AT04-R"], "M222M223.txt"),

    ]

    flatness_inputs = [

        ("320MHF1WCNT0159-AT07-R", ["M226M227-1.txt",""]),
        ("320MHF1WCNT0160-AT07-L", ["M226M227-1.txt",""]),
#        ("320MHL1WCNT0149-AT03-R", ["M216M217-1.txt",""]),
#        ("320MHL1WCNT0150-AT03-L", ["M216M217-1.txt",""]),
#        ("320MHR1WCNT0155-AT04-L", ["M222M223-1.txt",""]),
#        ("320MHR1WCNT0156-AT04-R", ["M222M223-1.txt",""]),

    ]

    main(offsets_inputs, flatness_inputs, tag = 'test')
