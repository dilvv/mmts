import sys

from optparse import OptionParser
import yaml

def Option_Parser(argv):

    usage='usage: %prog [options] arg\n'
    usage+='For more information, please see README !!!\n'
    parser = OptionParser(usage=usage)

    parser.add_option('-i', '--input',
            type='str', dest='input', default='tray.yaml',
            help=''
            )

    parser.add_option('-u', '--update',
            type='str', dest='update', default='assembly_tray-AT03-L.txt',
            help='Expected to be text files and the file name must satisfy XXX_AT0[0-9]-[LR].txt. You can use file1,file2,...'
            )

    (options, args) = parser.parse_args(argv)
    return options

def main(argv):

    options = Option_Parser(argv)

    with open(options.input) as old_file:
        old_file = yaml.safe_load(old_file)

    update_filenames = options.update.split(',')
    for filename in update_filenames:

        x = []
        y = []
        z = []

        with open(filename) as import_file:

            for line in import_file.readlines():
                if line.find("Focus1") != -1:
                    line_list = line.split()
                    x.append( float(line_list[2]) )
                    y.append( float(line_list[3]) )
                    z.append( float(line_list[4]) )

        filename_list = filename.split('/')[-1].split("-")
        tray_type = filename_list[-2]
        tray_side = filename_list[-1].split(".")[0]

        if not "plane" in old_file[tray_type]:
            old_file[tray_type]["plane"] = {}

        if not tray_side in old_file[tray_type]["plane"]:
            old_file[tray_type]["plane"][tray_side] = {}

        old_file[tray_type]["plane"][tray_side] = {
                        "x" : x,
                        "y" : y,
                        "z" : z,
                }

    with open(f"update_tray-{tray_type}-{tray_side}.yaml", "w") as new_file:
        yaml.dump(old_file, new_file)

if  __name__ == '__main__':
    sys.exit( main(sys.argv[1:]) )
