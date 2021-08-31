# Readme

Part of the code in the repository was adapted from https://github.com/pranav-s/brat2CoNLL

This repo contains code to convert Named entity recognition annotations in Brat standoff format to CoNLL format.
## Usage

The code assumes that all the input files i.e., *.ann and corresponding *.txt files are located in a single directory i.e., input_directory. Run the code to print the output of all annotations to the output_file.

    python brat2conll.py --input_dir={input_directory} --output_file={output_file}
    
##Warning

All discontinuous annotations are dropped for now and will be dealt with later

## References

[1] He, Jiayuan, et al. "Overview of chemu 2020: Named entity recognition and event extraction of chemical reactions from patents." International Conference of the Cross-Language Evaluation Forum for European Languages. Springer, Cham, 2020.
