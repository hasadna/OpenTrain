data = {}
data['00f6d726'] = []
data['02090d12'] = []
data['0297cb91eaf724cd'] = []
data['03242342'] = []
data['032b3544'] = []
data['03a4bf7f'] = []
data['043346a0'] = []
data['06df523b3f591ef5'] = []
data['071ba801'] = []
data['0756bb390dabe025'] = []
data['0c84b9e2'] = []
data['0c89639c69c4caf1'] = []
data['0d651c58'] = []
data['12ceee6f'] = []
data['1cb87f1e'] = []
data['1ea8bd8e2209b7a6'] = []
data['1fbbe499fee0a8f4'] = []
data['29a90ca7'] = []
data['2b85bf30'] = []
data['2c0e9b57'] = []
data['2dfc74b71c91677b'] = []
data['2ef1b758'] = []
data['368ad67702a58fdf'] = []
data['3c70f9b11f28734b'] = []
data['45e16c82'] = []
data['5355c362'] = []
data['5aedeb5b'] = []
data['5dc40476ad438414'] = []
data['639b264a'] = []
data['6a469b18'] = []
data['6dac01de293738ff'] = []
data['6f30dac6'] = []
data['6f87f12a'] = []
data['71_70d6006f83c00e2a'] = []
data['7c3a12e8'] = []
data['7dc78b6c'] = []
data['871d8773d36a2b8f'] = []
data['887e38a68fba876b'] = []
data['8890d50b'] = []
data['91b251f8'] = []
data['926c46a7'] = []
data['940e3161c577f921'] = []
data['9441706ac910c5da'] = []
data['992d69efe920047a'] = ['_00073'] # before gtfs - 16-6
data['9abb8365'] = []
data['9bc75282'] = []
data['a2402d42'] = []
data['a29c1c7e'] = []
data['a3db4699'] = []
data['a81da157'] = []
data['a8bb931e7c4a3285'] = []
data['ac1cb07e'] = []
data['ae59d76e'] = []
data['Amit_25556b5ee50f9ee5'] = []
data['Amit_81db2ecaa94d5377'] = []
data['Amit_e5066b39c330e434'] = []
data['b375c196e840cd96'] = []
data['ca86a698'] = []
data['cfd682b654b3f479'] = []
data['d22ab259f7f00884'] = []
data['d4065eef85aa51b8'] = []
data['d6093c45'] = []
data['d9e77fb9c6c851f4'] = []
data['dd_08faeb2238c71fa6'] = []
data['de46c33f'] = []
data['e4e504549d341ced'] = []
data['ed918429baaf8ab8'] = []
data['edf699494a2414cb'] = []
data['ee568383'] = []
data['eec00b8a751cd7dc'] = []
data['eefe93a6'] = []
data['eran27_8999f4c57498d973'] = []
data['eran28020910'] = []
data['eran_5060bdab5d871850'] = []
data['eran_63479c43eb54ff1f'] = []
data['eran_9c346249d6add4af'] = []
data['eran_b7fa2ccec8c127d2'] = []
data['eran_cf56f457bf123098'] = []
data['eran_d57316d7c8610535'] = []
data['eran_ec8d0d5fd1a16aed'] = []
data['f0a3692e1e9b2813'] = []
data['f406bdf1'] = []
data['f623a294be8a33eb'] = []
data['ff00668c'] = []
data['iocean_323b5911306012a9'] = []
data['iocean_977c890b5cac5e8a'] = []
data['noam_5dc97a9b4a7cb859'] = []
data['noam_8248e502621fa72c'] = []
data['ofer_207fabab5f381476'] = ['_00234', '_00271'] 
data['ofer_35a683e8b715a519'] = []
data['ofer_57656382027dc9c8'] = []
data['ofer_57dd77efa53ebe59'] = ['_00073'] # before gtfs - 16-6
data['ofer_5b464d8a30e09c06'] = []
data['ofer_6679d32261fd0845'] = []
data['ofer_7f6e334080aa725f'] = []
data['ofer_995357870c491cad'] = ['_00234', '_00266', '_00277']  
data['ofer_9d7d84b96a97b156'] = []
data['ofer_a7700dd1b90dea4c'] = []
data['ofer_a805c254139a38e9'] = []
data['ofer_b3b994f2ff17f4be'] = ['_00234']
data['ofer_ba71880ea2e0212f'] = []
data['ofer_d14be784eb8b6c6b'] = []
data['ofer_d64213d3f844903d'] = ['_00287', '_00234']
data['ofer_e402a16800ea3cc9'] = []
data['ofer_f8bb14c1c44712e9'] = []
data['tttt_4538a4b4118a6c80'] = []

if __name__ == '__main__':
    #print data info:
    import utils
    report_counts_and_dates = utils.get_report_counts_and_dates()
    for x in report_counts_and_dates:
        if x[2] in data:
            # date, report count, bssid, gtfs_trip_ids
            print x[0], x[1], x[2], data[x[2]]