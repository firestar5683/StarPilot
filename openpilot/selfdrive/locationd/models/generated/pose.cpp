#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_6769094018143345471) {
   out_6769094018143345471[0] = delta_x[0] + nom_x[0];
   out_6769094018143345471[1] = delta_x[1] + nom_x[1];
   out_6769094018143345471[2] = delta_x[2] + nom_x[2];
   out_6769094018143345471[3] = delta_x[3] + nom_x[3];
   out_6769094018143345471[4] = delta_x[4] + nom_x[4];
   out_6769094018143345471[5] = delta_x[5] + nom_x[5];
   out_6769094018143345471[6] = delta_x[6] + nom_x[6];
   out_6769094018143345471[7] = delta_x[7] + nom_x[7];
   out_6769094018143345471[8] = delta_x[8] + nom_x[8];
   out_6769094018143345471[9] = delta_x[9] + nom_x[9];
   out_6769094018143345471[10] = delta_x[10] + nom_x[10];
   out_6769094018143345471[11] = delta_x[11] + nom_x[11];
   out_6769094018143345471[12] = delta_x[12] + nom_x[12];
   out_6769094018143345471[13] = delta_x[13] + nom_x[13];
   out_6769094018143345471[14] = delta_x[14] + nom_x[14];
   out_6769094018143345471[15] = delta_x[15] + nom_x[15];
   out_6769094018143345471[16] = delta_x[16] + nom_x[16];
   out_6769094018143345471[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7105507959452432978) {
   out_7105507959452432978[0] = -nom_x[0] + true_x[0];
   out_7105507959452432978[1] = -nom_x[1] + true_x[1];
   out_7105507959452432978[2] = -nom_x[2] + true_x[2];
   out_7105507959452432978[3] = -nom_x[3] + true_x[3];
   out_7105507959452432978[4] = -nom_x[4] + true_x[4];
   out_7105507959452432978[5] = -nom_x[5] + true_x[5];
   out_7105507959452432978[6] = -nom_x[6] + true_x[6];
   out_7105507959452432978[7] = -nom_x[7] + true_x[7];
   out_7105507959452432978[8] = -nom_x[8] + true_x[8];
   out_7105507959452432978[9] = -nom_x[9] + true_x[9];
   out_7105507959452432978[10] = -nom_x[10] + true_x[10];
   out_7105507959452432978[11] = -nom_x[11] + true_x[11];
   out_7105507959452432978[12] = -nom_x[12] + true_x[12];
   out_7105507959452432978[13] = -nom_x[13] + true_x[13];
   out_7105507959452432978[14] = -nom_x[14] + true_x[14];
   out_7105507959452432978[15] = -nom_x[15] + true_x[15];
   out_7105507959452432978[16] = -nom_x[16] + true_x[16];
   out_7105507959452432978[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_6619985577834044559) {
   out_6619985577834044559[0] = 1.0;
   out_6619985577834044559[1] = 0.0;
   out_6619985577834044559[2] = 0.0;
   out_6619985577834044559[3] = 0.0;
   out_6619985577834044559[4] = 0.0;
   out_6619985577834044559[5] = 0.0;
   out_6619985577834044559[6] = 0.0;
   out_6619985577834044559[7] = 0.0;
   out_6619985577834044559[8] = 0.0;
   out_6619985577834044559[9] = 0.0;
   out_6619985577834044559[10] = 0.0;
   out_6619985577834044559[11] = 0.0;
   out_6619985577834044559[12] = 0.0;
   out_6619985577834044559[13] = 0.0;
   out_6619985577834044559[14] = 0.0;
   out_6619985577834044559[15] = 0.0;
   out_6619985577834044559[16] = 0.0;
   out_6619985577834044559[17] = 0.0;
   out_6619985577834044559[18] = 0.0;
   out_6619985577834044559[19] = 1.0;
   out_6619985577834044559[20] = 0.0;
   out_6619985577834044559[21] = 0.0;
   out_6619985577834044559[22] = 0.0;
   out_6619985577834044559[23] = 0.0;
   out_6619985577834044559[24] = 0.0;
   out_6619985577834044559[25] = 0.0;
   out_6619985577834044559[26] = 0.0;
   out_6619985577834044559[27] = 0.0;
   out_6619985577834044559[28] = 0.0;
   out_6619985577834044559[29] = 0.0;
   out_6619985577834044559[30] = 0.0;
   out_6619985577834044559[31] = 0.0;
   out_6619985577834044559[32] = 0.0;
   out_6619985577834044559[33] = 0.0;
   out_6619985577834044559[34] = 0.0;
   out_6619985577834044559[35] = 0.0;
   out_6619985577834044559[36] = 0.0;
   out_6619985577834044559[37] = 0.0;
   out_6619985577834044559[38] = 1.0;
   out_6619985577834044559[39] = 0.0;
   out_6619985577834044559[40] = 0.0;
   out_6619985577834044559[41] = 0.0;
   out_6619985577834044559[42] = 0.0;
   out_6619985577834044559[43] = 0.0;
   out_6619985577834044559[44] = 0.0;
   out_6619985577834044559[45] = 0.0;
   out_6619985577834044559[46] = 0.0;
   out_6619985577834044559[47] = 0.0;
   out_6619985577834044559[48] = 0.0;
   out_6619985577834044559[49] = 0.0;
   out_6619985577834044559[50] = 0.0;
   out_6619985577834044559[51] = 0.0;
   out_6619985577834044559[52] = 0.0;
   out_6619985577834044559[53] = 0.0;
   out_6619985577834044559[54] = 0.0;
   out_6619985577834044559[55] = 0.0;
   out_6619985577834044559[56] = 0.0;
   out_6619985577834044559[57] = 1.0;
   out_6619985577834044559[58] = 0.0;
   out_6619985577834044559[59] = 0.0;
   out_6619985577834044559[60] = 0.0;
   out_6619985577834044559[61] = 0.0;
   out_6619985577834044559[62] = 0.0;
   out_6619985577834044559[63] = 0.0;
   out_6619985577834044559[64] = 0.0;
   out_6619985577834044559[65] = 0.0;
   out_6619985577834044559[66] = 0.0;
   out_6619985577834044559[67] = 0.0;
   out_6619985577834044559[68] = 0.0;
   out_6619985577834044559[69] = 0.0;
   out_6619985577834044559[70] = 0.0;
   out_6619985577834044559[71] = 0.0;
   out_6619985577834044559[72] = 0.0;
   out_6619985577834044559[73] = 0.0;
   out_6619985577834044559[74] = 0.0;
   out_6619985577834044559[75] = 0.0;
   out_6619985577834044559[76] = 1.0;
   out_6619985577834044559[77] = 0.0;
   out_6619985577834044559[78] = 0.0;
   out_6619985577834044559[79] = 0.0;
   out_6619985577834044559[80] = 0.0;
   out_6619985577834044559[81] = 0.0;
   out_6619985577834044559[82] = 0.0;
   out_6619985577834044559[83] = 0.0;
   out_6619985577834044559[84] = 0.0;
   out_6619985577834044559[85] = 0.0;
   out_6619985577834044559[86] = 0.0;
   out_6619985577834044559[87] = 0.0;
   out_6619985577834044559[88] = 0.0;
   out_6619985577834044559[89] = 0.0;
   out_6619985577834044559[90] = 0.0;
   out_6619985577834044559[91] = 0.0;
   out_6619985577834044559[92] = 0.0;
   out_6619985577834044559[93] = 0.0;
   out_6619985577834044559[94] = 0.0;
   out_6619985577834044559[95] = 1.0;
   out_6619985577834044559[96] = 0.0;
   out_6619985577834044559[97] = 0.0;
   out_6619985577834044559[98] = 0.0;
   out_6619985577834044559[99] = 0.0;
   out_6619985577834044559[100] = 0.0;
   out_6619985577834044559[101] = 0.0;
   out_6619985577834044559[102] = 0.0;
   out_6619985577834044559[103] = 0.0;
   out_6619985577834044559[104] = 0.0;
   out_6619985577834044559[105] = 0.0;
   out_6619985577834044559[106] = 0.0;
   out_6619985577834044559[107] = 0.0;
   out_6619985577834044559[108] = 0.0;
   out_6619985577834044559[109] = 0.0;
   out_6619985577834044559[110] = 0.0;
   out_6619985577834044559[111] = 0.0;
   out_6619985577834044559[112] = 0.0;
   out_6619985577834044559[113] = 0.0;
   out_6619985577834044559[114] = 1.0;
   out_6619985577834044559[115] = 0.0;
   out_6619985577834044559[116] = 0.0;
   out_6619985577834044559[117] = 0.0;
   out_6619985577834044559[118] = 0.0;
   out_6619985577834044559[119] = 0.0;
   out_6619985577834044559[120] = 0.0;
   out_6619985577834044559[121] = 0.0;
   out_6619985577834044559[122] = 0.0;
   out_6619985577834044559[123] = 0.0;
   out_6619985577834044559[124] = 0.0;
   out_6619985577834044559[125] = 0.0;
   out_6619985577834044559[126] = 0.0;
   out_6619985577834044559[127] = 0.0;
   out_6619985577834044559[128] = 0.0;
   out_6619985577834044559[129] = 0.0;
   out_6619985577834044559[130] = 0.0;
   out_6619985577834044559[131] = 0.0;
   out_6619985577834044559[132] = 0.0;
   out_6619985577834044559[133] = 1.0;
   out_6619985577834044559[134] = 0.0;
   out_6619985577834044559[135] = 0.0;
   out_6619985577834044559[136] = 0.0;
   out_6619985577834044559[137] = 0.0;
   out_6619985577834044559[138] = 0.0;
   out_6619985577834044559[139] = 0.0;
   out_6619985577834044559[140] = 0.0;
   out_6619985577834044559[141] = 0.0;
   out_6619985577834044559[142] = 0.0;
   out_6619985577834044559[143] = 0.0;
   out_6619985577834044559[144] = 0.0;
   out_6619985577834044559[145] = 0.0;
   out_6619985577834044559[146] = 0.0;
   out_6619985577834044559[147] = 0.0;
   out_6619985577834044559[148] = 0.0;
   out_6619985577834044559[149] = 0.0;
   out_6619985577834044559[150] = 0.0;
   out_6619985577834044559[151] = 0.0;
   out_6619985577834044559[152] = 1.0;
   out_6619985577834044559[153] = 0.0;
   out_6619985577834044559[154] = 0.0;
   out_6619985577834044559[155] = 0.0;
   out_6619985577834044559[156] = 0.0;
   out_6619985577834044559[157] = 0.0;
   out_6619985577834044559[158] = 0.0;
   out_6619985577834044559[159] = 0.0;
   out_6619985577834044559[160] = 0.0;
   out_6619985577834044559[161] = 0.0;
   out_6619985577834044559[162] = 0.0;
   out_6619985577834044559[163] = 0.0;
   out_6619985577834044559[164] = 0.0;
   out_6619985577834044559[165] = 0.0;
   out_6619985577834044559[166] = 0.0;
   out_6619985577834044559[167] = 0.0;
   out_6619985577834044559[168] = 0.0;
   out_6619985577834044559[169] = 0.0;
   out_6619985577834044559[170] = 0.0;
   out_6619985577834044559[171] = 1.0;
   out_6619985577834044559[172] = 0.0;
   out_6619985577834044559[173] = 0.0;
   out_6619985577834044559[174] = 0.0;
   out_6619985577834044559[175] = 0.0;
   out_6619985577834044559[176] = 0.0;
   out_6619985577834044559[177] = 0.0;
   out_6619985577834044559[178] = 0.0;
   out_6619985577834044559[179] = 0.0;
   out_6619985577834044559[180] = 0.0;
   out_6619985577834044559[181] = 0.0;
   out_6619985577834044559[182] = 0.0;
   out_6619985577834044559[183] = 0.0;
   out_6619985577834044559[184] = 0.0;
   out_6619985577834044559[185] = 0.0;
   out_6619985577834044559[186] = 0.0;
   out_6619985577834044559[187] = 0.0;
   out_6619985577834044559[188] = 0.0;
   out_6619985577834044559[189] = 0.0;
   out_6619985577834044559[190] = 1.0;
   out_6619985577834044559[191] = 0.0;
   out_6619985577834044559[192] = 0.0;
   out_6619985577834044559[193] = 0.0;
   out_6619985577834044559[194] = 0.0;
   out_6619985577834044559[195] = 0.0;
   out_6619985577834044559[196] = 0.0;
   out_6619985577834044559[197] = 0.0;
   out_6619985577834044559[198] = 0.0;
   out_6619985577834044559[199] = 0.0;
   out_6619985577834044559[200] = 0.0;
   out_6619985577834044559[201] = 0.0;
   out_6619985577834044559[202] = 0.0;
   out_6619985577834044559[203] = 0.0;
   out_6619985577834044559[204] = 0.0;
   out_6619985577834044559[205] = 0.0;
   out_6619985577834044559[206] = 0.0;
   out_6619985577834044559[207] = 0.0;
   out_6619985577834044559[208] = 0.0;
   out_6619985577834044559[209] = 1.0;
   out_6619985577834044559[210] = 0.0;
   out_6619985577834044559[211] = 0.0;
   out_6619985577834044559[212] = 0.0;
   out_6619985577834044559[213] = 0.0;
   out_6619985577834044559[214] = 0.0;
   out_6619985577834044559[215] = 0.0;
   out_6619985577834044559[216] = 0.0;
   out_6619985577834044559[217] = 0.0;
   out_6619985577834044559[218] = 0.0;
   out_6619985577834044559[219] = 0.0;
   out_6619985577834044559[220] = 0.0;
   out_6619985577834044559[221] = 0.0;
   out_6619985577834044559[222] = 0.0;
   out_6619985577834044559[223] = 0.0;
   out_6619985577834044559[224] = 0.0;
   out_6619985577834044559[225] = 0.0;
   out_6619985577834044559[226] = 0.0;
   out_6619985577834044559[227] = 0.0;
   out_6619985577834044559[228] = 1.0;
   out_6619985577834044559[229] = 0.0;
   out_6619985577834044559[230] = 0.0;
   out_6619985577834044559[231] = 0.0;
   out_6619985577834044559[232] = 0.0;
   out_6619985577834044559[233] = 0.0;
   out_6619985577834044559[234] = 0.0;
   out_6619985577834044559[235] = 0.0;
   out_6619985577834044559[236] = 0.0;
   out_6619985577834044559[237] = 0.0;
   out_6619985577834044559[238] = 0.0;
   out_6619985577834044559[239] = 0.0;
   out_6619985577834044559[240] = 0.0;
   out_6619985577834044559[241] = 0.0;
   out_6619985577834044559[242] = 0.0;
   out_6619985577834044559[243] = 0.0;
   out_6619985577834044559[244] = 0.0;
   out_6619985577834044559[245] = 0.0;
   out_6619985577834044559[246] = 0.0;
   out_6619985577834044559[247] = 1.0;
   out_6619985577834044559[248] = 0.0;
   out_6619985577834044559[249] = 0.0;
   out_6619985577834044559[250] = 0.0;
   out_6619985577834044559[251] = 0.0;
   out_6619985577834044559[252] = 0.0;
   out_6619985577834044559[253] = 0.0;
   out_6619985577834044559[254] = 0.0;
   out_6619985577834044559[255] = 0.0;
   out_6619985577834044559[256] = 0.0;
   out_6619985577834044559[257] = 0.0;
   out_6619985577834044559[258] = 0.0;
   out_6619985577834044559[259] = 0.0;
   out_6619985577834044559[260] = 0.0;
   out_6619985577834044559[261] = 0.0;
   out_6619985577834044559[262] = 0.0;
   out_6619985577834044559[263] = 0.0;
   out_6619985577834044559[264] = 0.0;
   out_6619985577834044559[265] = 0.0;
   out_6619985577834044559[266] = 1.0;
   out_6619985577834044559[267] = 0.0;
   out_6619985577834044559[268] = 0.0;
   out_6619985577834044559[269] = 0.0;
   out_6619985577834044559[270] = 0.0;
   out_6619985577834044559[271] = 0.0;
   out_6619985577834044559[272] = 0.0;
   out_6619985577834044559[273] = 0.0;
   out_6619985577834044559[274] = 0.0;
   out_6619985577834044559[275] = 0.0;
   out_6619985577834044559[276] = 0.0;
   out_6619985577834044559[277] = 0.0;
   out_6619985577834044559[278] = 0.0;
   out_6619985577834044559[279] = 0.0;
   out_6619985577834044559[280] = 0.0;
   out_6619985577834044559[281] = 0.0;
   out_6619985577834044559[282] = 0.0;
   out_6619985577834044559[283] = 0.0;
   out_6619985577834044559[284] = 0.0;
   out_6619985577834044559[285] = 1.0;
   out_6619985577834044559[286] = 0.0;
   out_6619985577834044559[287] = 0.0;
   out_6619985577834044559[288] = 0.0;
   out_6619985577834044559[289] = 0.0;
   out_6619985577834044559[290] = 0.0;
   out_6619985577834044559[291] = 0.0;
   out_6619985577834044559[292] = 0.0;
   out_6619985577834044559[293] = 0.0;
   out_6619985577834044559[294] = 0.0;
   out_6619985577834044559[295] = 0.0;
   out_6619985577834044559[296] = 0.0;
   out_6619985577834044559[297] = 0.0;
   out_6619985577834044559[298] = 0.0;
   out_6619985577834044559[299] = 0.0;
   out_6619985577834044559[300] = 0.0;
   out_6619985577834044559[301] = 0.0;
   out_6619985577834044559[302] = 0.0;
   out_6619985577834044559[303] = 0.0;
   out_6619985577834044559[304] = 1.0;
   out_6619985577834044559[305] = 0.0;
   out_6619985577834044559[306] = 0.0;
   out_6619985577834044559[307] = 0.0;
   out_6619985577834044559[308] = 0.0;
   out_6619985577834044559[309] = 0.0;
   out_6619985577834044559[310] = 0.0;
   out_6619985577834044559[311] = 0.0;
   out_6619985577834044559[312] = 0.0;
   out_6619985577834044559[313] = 0.0;
   out_6619985577834044559[314] = 0.0;
   out_6619985577834044559[315] = 0.0;
   out_6619985577834044559[316] = 0.0;
   out_6619985577834044559[317] = 0.0;
   out_6619985577834044559[318] = 0.0;
   out_6619985577834044559[319] = 0.0;
   out_6619985577834044559[320] = 0.0;
   out_6619985577834044559[321] = 0.0;
   out_6619985577834044559[322] = 0.0;
   out_6619985577834044559[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8911446702564060395) {
   out_8911446702564060395[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8911446702564060395[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8911446702564060395[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8911446702564060395[3] = dt*state[12] + state[3];
   out_8911446702564060395[4] = dt*state[13] + state[4];
   out_8911446702564060395[5] = dt*state[14] + state[5];
   out_8911446702564060395[6] = state[6];
   out_8911446702564060395[7] = state[7];
   out_8911446702564060395[8] = state[8];
   out_8911446702564060395[9] = state[9];
   out_8911446702564060395[10] = state[10];
   out_8911446702564060395[11] = state[11];
   out_8911446702564060395[12] = state[12];
   out_8911446702564060395[13] = state[13];
   out_8911446702564060395[14] = state[14];
   out_8911446702564060395[15] = state[15];
   out_8911446702564060395[16] = state[16];
   out_8911446702564060395[17] = state[17];
}
void F_fun(double *state, double dt, double *out_8001086797165012903) {
   out_8001086797165012903[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8001086797165012903[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8001086797165012903[2] = 0;
   out_8001086797165012903[3] = 0;
   out_8001086797165012903[4] = 0;
   out_8001086797165012903[5] = 0;
   out_8001086797165012903[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8001086797165012903[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8001086797165012903[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_8001086797165012903[9] = 0;
   out_8001086797165012903[10] = 0;
   out_8001086797165012903[11] = 0;
   out_8001086797165012903[12] = 0;
   out_8001086797165012903[13] = 0;
   out_8001086797165012903[14] = 0;
   out_8001086797165012903[15] = 0;
   out_8001086797165012903[16] = 0;
   out_8001086797165012903[17] = 0;
   out_8001086797165012903[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8001086797165012903[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8001086797165012903[20] = 0;
   out_8001086797165012903[21] = 0;
   out_8001086797165012903[22] = 0;
   out_8001086797165012903[23] = 0;
   out_8001086797165012903[24] = 0;
   out_8001086797165012903[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8001086797165012903[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_8001086797165012903[27] = 0;
   out_8001086797165012903[28] = 0;
   out_8001086797165012903[29] = 0;
   out_8001086797165012903[30] = 0;
   out_8001086797165012903[31] = 0;
   out_8001086797165012903[32] = 0;
   out_8001086797165012903[33] = 0;
   out_8001086797165012903[34] = 0;
   out_8001086797165012903[35] = 0;
   out_8001086797165012903[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8001086797165012903[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8001086797165012903[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8001086797165012903[39] = 0;
   out_8001086797165012903[40] = 0;
   out_8001086797165012903[41] = 0;
   out_8001086797165012903[42] = 0;
   out_8001086797165012903[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8001086797165012903[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_8001086797165012903[45] = 0;
   out_8001086797165012903[46] = 0;
   out_8001086797165012903[47] = 0;
   out_8001086797165012903[48] = 0;
   out_8001086797165012903[49] = 0;
   out_8001086797165012903[50] = 0;
   out_8001086797165012903[51] = 0;
   out_8001086797165012903[52] = 0;
   out_8001086797165012903[53] = 0;
   out_8001086797165012903[54] = 0;
   out_8001086797165012903[55] = 0;
   out_8001086797165012903[56] = 0;
   out_8001086797165012903[57] = 1;
   out_8001086797165012903[58] = 0;
   out_8001086797165012903[59] = 0;
   out_8001086797165012903[60] = 0;
   out_8001086797165012903[61] = 0;
   out_8001086797165012903[62] = 0;
   out_8001086797165012903[63] = 0;
   out_8001086797165012903[64] = 0;
   out_8001086797165012903[65] = 0;
   out_8001086797165012903[66] = dt;
   out_8001086797165012903[67] = 0;
   out_8001086797165012903[68] = 0;
   out_8001086797165012903[69] = 0;
   out_8001086797165012903[70] = 0;
   out_8001086797165012903[71] = 0;
   out_8001086797165012903[72] = 0;
   out_8001086797165012903[73] = 0;
   out_8001086797165012903[74] = 0;
   out_8001086797165012903[75] = 0;
   out_8001086797165012903[76] = 1;
   out_8001086797165012903[77] = 0;
   out_8001086797165012903[78] = 0;
   out_8001086797165012903[79] = 0;
   out_8001086797165012903[80] = 0;
   out_8001086797165012903[81] = 0;
   out_8001086797165012903[82] = 0;
   out_8001086797165012903[83] = 0;
   out_8001086797165012903[84] = 0;
   out_8001086797165012903[85] = dt;
   out_8001086797165012903[86] = 0;
   out_8001086797165012903[87] = 0;
   out_8001086797165012903[88] = 0;
   out_8001086797165012903[89] = 0;
   out_8001086797165012903[90] = 0;
   out_8001086797165012903[91] = 0;
   out_8001086797165012903[92] = 0;
   out_8001086797165012903[93] = 0;
   out_8001086797165012903[94] = 0;
   out_8001086797165012903[95] = 1;
   out_8001086797165012903[96] = 0;
   out_8001086797165012903[97] = 0;
   out_8001086797165012903[98] = 0;
   out_8001086797165012903[99] = 0;
   out_8001086797165012903[100] = 0;
   out_8001086797165012903[101] = 0;
   out_8001086797165012903[102] = 0;
   out_8001086797165012903[103] = 0;
   out_8001086797165012903[104] = dt;
   out_8001086797165012903[105] = 0;
   out_8001086797165012903[106] = 0;
   out_8001086797165012903[107] = 0;
   out_8001086797165012903[108] = 0;
   out_8001086797165012903[109] = 0;
   out_8001086797165012903[110] = 0;
   out_8001086797165012903[111] = 0;
   out_8001086797165012903[112] = 0;
   out_8001086797165012903[113] = 0;
   out_8001086797165012903[114] = 1;
   out_8001086797165012903[115] = 0;
   out_8001086797165012903[116] = 0;
   out_8001086797165012903[117] = 0;
   out_8001086797165012903[118] = 0;
   out_8001086797165012903[119] = 0;
   out_8001086797165012903[120] = 0;
   out_8001086797165012903[121] = 0;
   out_8001086797165012903[122] = 0;
   out_8001086797165012903[123] = 0;
   out_8001086797165012903[124] = 0;
   out_8001086797165012903[125] = 0;
   out_8001086797165012903[126] = 0;
   out_8001086797165012903[127] = 0;
   out_8001086797165012903[128] = 0;
   out_8001086797165012903[129] = 0;
   out_8001086797165012903[130] = 0;
   out_8001086797165012903[131] = 0;
   out_8001086797165012903[132] = 0;
   out_8001086797165012903[133] = 1;
   out_8001086797165012903[134] = 0;
   out_8001086797165012903[135] = 0;
   out_8001086797165012903[136] = 0;
   out_8001086797165012903[137] = 0;
   out_8001086797165012903[138] = 0;
   out_8001086797165012903[139] = 0;
   out_8001086797165012903[140] = 0;
   out_8001086797165012903[141] = 0;
   out_8001086797165012903[142] = 0;
   out_8001086797165012903[143] = 0;
   out_8001086797165012903[144] = 0;
   out_8001086797165012903[145] = 0;
   out_8001086797165012903[146] = 0;
   out_8001086797165012903[147] = 0;
   out_8001086797165012903[148] = 0;
   out_8001086797165012903[149] = 0;
   out_8001086797165012903[150] = 0;
   out_8001086797165012903[151] = 0;
   out_8001086797165012903[152] = 1;
   out_8001086797165012903[153] = 0;
   out_8001086797165012903[154] = 0;
   out_8001086797165012903[155] = 0;
   out_8001086797165012903[156] = 0;
   out_8001086797165012903[157] = 0;
   out_8001086797165012903[158] = 0;
   out_8001086797165012903[159] = 0;
   out_8001086797165012903[160] = 0;
   out_8001086797165012903[161] = 0;
   out_8001086797165012903[162] = 0;
   out_8001086797165012903[163] = 0;
   out_8001086797165012903[164] = 0;
   out_8001086797165012903[165] = 0;
   out_8001086797165012903[166] = 0;
   out_8001086797165012903[167] = 0;
   out_8001086797165012903[168] = 0;
   out_8001086797165012903[169] = 0;
   out_8001086797165012903[170] = 0;
   out_8001086797165012903[171] = 1;
   out_8001086797165012903[172] = 0;
   out_8001086797165012903[173] = 0;
   out_8001086797165012903[174] = 0;
   out_8001086797165012903[175] = 0;
   out_8001086797165012903[176] = 0;
   out_8001086797165012903[177] = 0;
   out_8001086797165012903[178] = 0;
   out_8001086797165012903[179] = 0;
   out_8001086797165012903[180] = 0;
   out_8001086797165012903[181] = 0;
   out_8001086797165012903[182] = 0;
   out_8001086797165012903[183] = 0;
   out_8001086797165012903[184] = 0;
   out_8001086797165012903[185] = 0;
   out_8001086797165012903[186] = 0;
   out_8001086797165012903[187] = 0;
   out_8001086797165012903[188] = 0;
   out_8001086797165012903[189] = 0;
   out_8001086797165012903[190] = 1;
   out_8001086797165012903[191] = 0;
   out_8001086797165012903[192] = 0;
   out_8001086797165012903[193] = 0;
   out_8001086797165012903[194] = 0;
   out_8001086797165012903[195] = 0;
   out_8001086797165012903[196] = 0;
   out_8001086797165012903[197] = 0;
   out_8001086797165012903[198] = 0;
   out_8001086797165012903[199] = 0;
   out_8001086797165012903[200] = 0;
   out_8001086797165012903[201] = 0;
   out_8001086797165012903[202] = 0;
   out_8001086797165012903[203] = 0;
   out_8001086797165012903[204] = 0;
   out_8001086797165012903[205] = 0;
   out_8001086797165012903[206] = 0;
   out_8001086797165012903[207] = 0;
   out_8001086797165012903[208] = 0;
   out_8001086797165012903[209] = 1;
   out_8001086797165012903[210] = 0;
   out_8001086797165012903[211] = 0;
   out_8001086797165012903[212] = 0;
   out_8001086797165012903[213] = 0;
   out_8001086797165012903[214] = 0;
   out_8001086797165012903[215] = 0;
   out_8001086797165012903[216] = 0;
   out_8001086797165012903[217] = 0;
   out_8001086797165012903[218] = 0;
   out_8001086797165012903[219] = 0;
   out_8001086797165012903[220] = 0;
   out_8001086797165012903[221] = 0;
   out_8001086797165012903[222] = 0;
   out_8001086797165012903[223] = 0;
   out_8001086797165012903[224] = 0;
   out_8001086797165012903[225] = 0;
   out_8001086797165012903[226] = 0;
   out_8001086797165012903[227] = 0;
   out_8001086797165012903[228] = 1;
   out_8001086797165012903[229] = 0;
   out_8001086797165012903[230] = 0;
   out_8001086797165012903[231] = 0;
   out_8001086797165012903[232] = 0;
   out_8001086797165012903[233] = 0;
   out_8001086797165012903[234] = 0;
   out_8001086797165012903[235] = 0;
   out_8001086797165012903[236] = 0;
   out_8001086797165012903[237] = 0;
   out_8001086797165012903[238] = 0;
   out_8001086797165012903[239] = 0;
   out_8001086797165012903[240] = 0;
   out_8001086797165012903[241] = 0;
   out_8001086797165012903[242] = 0;
   out_8001086797165012903[243] = 0;
   out_8001086797165012903[244] = 0;
   out_8001086797165012903[245] = 0;
   out_8001086797165012903[246] = 0;
   out_8001086797165012903[247] = 1;
   out_8001086797165012903[248] = 0;
   out_8001086797165012903[249] = 0;
   out_8001086797165012903[250] = 0;
   out_8001086797165012903[251] = 0;
   out_8001086797165012903[252] = 0;
   out_8001086797165012903[253] = 0;
   out_8001086797165012903[254] = 0;
   out_8001086797165012903[255] = 0;
   out_8001086797165012903[256] = 0;
   out_8001086797165012903[257] = 0;
   out_8001086797165012903[258] = 0;
   out_8001086797165012903[259] = 0;
   out_8001086797165012903[260] = 0;
   out_8001086797165012903[261] = 0;
   out_8001086797165012903[262] = 0;
   out_8001086797165012903[263] = 0;
   out_8001086797165012903[264] = 0;
   out_8001086797165012903[265] = 0;
   out_8001086797165012903[266] = 1;
   out_8001086797165012903[267] = 0;
   out_8001086797165012903[268] = 0;
   out_8001086797165012903[269] = 0;
   out_8001086797165012903[270] = 0;
   out_8001086797165012903[271] = 0;
   out_8001086797165012903[272] = 0;
   out_8001086797165012903[273] = 0;
   out_8001086797165012903[274] = 0;
   out_8001086797165012903[275] = 0;
   out_8001086797165012903[276] = 0;
   out_8001086797165012903[277] = 0;
   out_8001086797165012903[278] = 0;
   out_8001086797165012903[279] = 0;
   out_8001086797165012903[280] = 0;
   out_8001086797165012903[281] = 0;
   out_8001086797165012903[282] = 0;
   out_8001086797165012903[283] = 0;
   out_8001086797165012903[284] = 0;
   out_8001086797165012903[285] = 1;
   out_8001086797165012903[286] = 0;
   out_8001086797165012903[287] = 0;
   out_8001086797165012903[288] = 0;
   out_8001086797165012903[289] = 0;
   out_8001086797165012903[290] = 0;
   out_8001086797165012903[291] = 0;
   out_8001086797165012903[292] = 0;
   out_8001086797165012903[293] = 0;
   out_8001086797165012903[294] = 0;
   out_8001086797165012903[295] = 0;
   out_8001086797165012903[296] = 0;
   out_8001086797165012903[297] = 0;
   out_8001086797165012903[298] = 0;
   out_8001086797165012903[299] = 0;
   out_8001086797165012903[300] = 0;
   out_8001086797165012903[301] = 0;
   out_8001086797165012903[302] = 0;
   out_8001086797165012903[303] = 0;
   out_8001086797165012903[304] = 1;
   out_8001086797165012903[305] = 0;
   out_8001086797165012903[306] = 0;
   out_8001086797165012903[307] = 0;
   out_8001086797165012903[308] = 0;
   out_8001086797165012903[309] = 0;
   out_8001086797165012903[310] = 0;
   out_8001086797165012903[311] = 0;
   out_8001086797165012903[312] = 0;
   out_8001086797165012903[313] = 0;
   out_8001086797165012903[314] = 0;
   out_8001086797165012903[315] = 0;
   out_8001086797165012903[316] = 0;
   out_8001086797165012903[317] = 0;
   out_8001086797165012903[318] = 0;
   out_8001086797165012903[319] = 0;
   out_8001086797165012903[320] = 0;
   out_8001086797165012903[321] = 0;
   out_8001086797165012903[322] = 0;
   out_8001086797165012903[323] = 1;
}
void h_4(double *state, double *unused, double *out_700157376215369055) {
   out_700157376215369055[0] = state[6] + state[9];
   out_700157376215369055[1] = state[7] + state[10];
   out_700157376215369055[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_5040670747730128630) {
   out_5040670747730128630[0] = 0;
   out_5040670747730128630[1] = 0;
   out_5040670747730128630[2] = 0;
   out_5040670747730128630[3] = 0;
   out_5040670747730128630[4] = 0;
   out_5040670747730128630[5] = 0;
   out_5040670747730128630[6] = 1;
   out_5040670747730128630[7] = 0;
   out_5040670747730128630[8] = 0;
   out_5040670747730128630[9] = 1;
   out_5040670747730128630[10] = 0;
   out_5040670747730128630[11] = 0;
   out_5040670747730128630[12] = 0;
   out_5040670747730128630[13] = 0;
   out_5040670747730128630[14] = 0;
   out_5040670747730128630[15] = 0;
   out_5040670747730128630[16] = 0;
   out_5040670747730128630[17] = 0;
   out_5040670747730128630[18] = 0;
   out_5040670747730128630[19] = 0;
   out_5040670747730128630[20] = 0;
   out_5040670747730128630[21] = 0;
   out_5040670747730128630[22] = 0;
   out_5040670747730128630[23] = 0;
   out_5040670747730128630[24] = 0;
   out_5040670747730128630[25] = 1;
   out_5040670747730128630[26] = 0;
   out_5040670747730128630[27] = 0;
   out_5040670747730128630[28] = 1;
   out_5040670747730128630[29] = 0;
   out_5040670747730128630[30] = 0;
   out_5040670747730128630[31] = 0;
   out_5040670747730128630[32] = 0;
   out_5040670747730128630[33] = 0;
   out_5040670747730128630[34] = 0;
   out_5040670747730128630[35] = 0;
   out_5040670747730128630[36] = 0;
   out_5040670747730128630[37] = 0;
   out_5040670747730128630[38] = 0;
   out_5040670747730128630[39] = 0;
   out_5040670747730128630[40] = 0;
   out_5040670747730128630[41] = 0;
   out_5040670747730128630[42] = 0;
   out_5040670747730128630[43] = 0;
   out_5040670747730128630[44] = 1;
   out_5040670747730128630[45] = 0;
   out_5040670747730128630[46] = 0;
   out_5040670747730128630[47] = 1;
   out_5040670747730128630[48] = 0;
   out_5040670747730128630[49] = 0;
   out_5040670747730128630[50] = 0;
   out_5040670747730128630[51] = 0;
   out_5040670747730128630[52] = 0;
   out_5040670747730128630[53] = 0;
}
void h_10(double *state, double *unused, double *out_157308656343122283) {
   out_157308656343122283[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_157308656343122283[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_157308656343122283[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_6282647945703286816) {
   out_6282647945703286816[0] = 0;
   out_6282647945703286816[1] = 9.8100000000000005*cos(state[1]);
   out_6282647945703286816[2] = 0;
   out_6282647945703286816[3] = 0;
   out_6282647945703286816[4] = -state[8];
   out_6282647945703286816[5] = state[7];
   out_6282647945703286816[6] = 0;
   out_6282647945703286816[7] = state[5];
   out_6282647945703286816[8] = -state[4];
   out_6282647945703286816[9] = 0;
   out_6282647945703286816[10] = 0;
   out_6282647945703286816[11] = 0;
   out_6282647945703286816[12] = 1;
   out_6282647945703286816[13] = 0;
   out_6282647945703286816[14] = 0;
   out_6282647945703286816[15] = 1;
   out_6282647945703286816[16] = 0;
   out_6282647945703286816[17] = 0;
   out_6282647945703286816[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_6282647945703286816[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_6282647945703286816[20] = 0;
   out_6282647945703286816[21] = state[8];
   out_6282647945703286816[22] = 0;
   out_6282647945703286816[23] = -state[6];
   out_6282647945703286816[24] = -state[5];
   out_6282647945703286816[25] = 0;
   out_6282647945703286816[26] = state[3];
   out_6282647945703286816[27] = 0;
   out_6282647945703286816[28] = 0;
   out_6282647945703286816[29] = 0;
   out_6282647945703286816[30] = 0;
   out_6282647945703286816[31] = 1;
   out_6282647945703286816[32] = 0;
   out_6282647945703286816[33] = 0;
   out_6282647945703286816[34] = 1;
   out_6282647945703286816[35] = 0;
   out_6282647945703286816[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_6282647945703286816[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_6282647945703286816[38] = 0;
   out_6282647945703286816[39] = -state[7];
   out_6282647945703286816[40] = state[6];
   out_6282647945703286816[41] = 0;
   out_6282647945703286816[42] = state[4];
   out_6282647945703286816[43] = -state[3];
   out_6282647945703286816[44] = 0;
   out_6282647945703286816[45] = 0;
   out_6282647945703286816[46] = 0;
   out_6282647945703286816[47] = 0;
   out_6282647945703286816[48] = 0;
   out_6282647945703286816[49] = 0;
   out_6282647945703286816[50] = 1;
   out_6282647945703286816[51] = 0;
   out_6282647945703286816[52] = 0;
   out_6282647945703286816[53] = 1;
}
void h_13(double *state, double *unused, double *out_8562780767398180943) {
   out_8562780767398180943[0] = state[3];
   out_8562780767398180943[1] = state[4];
   out_8562780767398180943[2] = state[5];
}
void H_13(double *state, double *unused, double *out_5795442117662722057) {
   out_5795442117662722057[0] = 0;
   out_5795442117662722057[1] = 0;
   out_5795442117662722057[2] = 0;
   out_5795442117662722057[3] = 1;
   out_5795442117662722057[4] = 0;
   out_5795442117662722057[5] = 0;
   out_5795442117662722057[6] = 0;
   out_5795442117662722057[7] = 0;
   out_5795442117662722057[8] = 0;
   out_5795442117662722057[9] = 0;
   out_5795442117662722057[10] = 0;
   out_5795442117662722057[11] = 0;
   out_5795442117662722057[12] = 0;
   out_5795442117662722057[13] = 0;
   out_5795442117662722057[14] = 0;
   out_5795442117662722057[15] = 0;
   out_5795442117662722057[16] = 0;
   out_5795442117662722057[17] = 0;
   out_5795442117662722057[18] = 0;
   out_5795442117662722057[19] = 0;
   out_5795442117662722057[20] = 0;
   out_5795442117662722057[21] = 0;
   out_5795442117662722057[22] = 1;
   out_5795442117662722057[23] = 0;
   out_5795442117662722057[24] = 0;
   out_5795442117662722057[25] = 0;
   out_5795442117662722057[26] = 0;
   out_5795442117662722057[27] = 0;
   out_5795442117662722057[28] = 0;
   out_5795442117662722057[29] = 0;
   out_5795442117662722057[30] = 0;
   out_5795442117662722057[31] = 0;
   out_5795442117662722057[32] = 0;
   out_5795442117662722057[33] = 0;
   out_5795442117662722057[34] = 0;
   out_5795442117662722057[35] = 0;
   out_5795442117662722057[36] = 0;
   out_5795442117662722057[37] = 0;
   out_5795442117662722057[38] = 0;
   out_5795442117662722057[39] = 0;
   out_5795442117662722057[40] = 0;
   out_5795442117662722057[41] = 1;
   out_5795442117662722057[42] = 0;
   out_5795442117662722057[43] = 0;
   out_5795442117662722057[44] = 0;
   out_5795442117662722057[45] = 0;
   out_5795442117662722057[46] = 0;
   out_5795442117662722057[47] = 0;
   out_5795442117662722057[48] = 0;
   out_5795442117662722057[49] = 0;
   out_5795442117662722057[50] = 0;
   out_5795442117662722057[51] = 0;
   out_5795442117662722057[52] = 0;
   out_5795442117662722057[53] = 0;
}
void h_14(double *state, double *unused, double *out_8175075787359245864) {
   out_8175075787359245864[0] = state[6];
   out_8175075787359245864[1] = state[7];
   out_8175075787359245864[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1957882315434756334) {
   out_1957882315434756334[0] = 0;
   out_1957882315434756334[1] = 0;
   out_1957882315434756334[2] = 0;
   out_1957882315434756334[3] = 0;
   out_1957882315434756334[4] = 0;
   out_1957882315434756334[5] = 0;
   out_1957882315434756334[6] = 1;
   out_1957882315434756334[7] = 0;
   out_1957882315434756334[8] = 0;
   out_1957882315434756334[9] = 0;
   out_1957882315434756334[10] = 0;
   out_1957882315434756334[11] = 0;
   out_1957882315434756334[12] = 0;
   out_1957882315434756334[13] = 0;
   out_1957882315434756334[14] = 0;
   out_1957882315434756334[15] = 0;
   out_1957882315434756334[16] = 0;
   out_1957882315434756334[17] = 0;
   out_1957882315434756334[18] = 0;
   out_1957882315434756334[19] = 0;
   out_1957882315434756334[20] = 0;
   out_1957882315434756334[21] = 0;
   out_1957882315434756334[22] = 0;
   out_1957882315434756334[23] = 0;
   out_1957882315434756334[24] = 0;
   out_1957882315434756334[25] = 1;
   out_1957882315434756334[26] = 0;
   out_1957882315434756334[27] = 0;
   out_1957882315434756334[28] = 0;
   out_1957882315434756334[29] = 0;
   out_1957882315434756334[30] = 0;
   out_1957882315434756334[31] = 0;
   out_1957882315434756334[32] = 0;
   out_1957882315434756334[33] = 0;
   out_1957882315434756334[34] = 0;
   out_1957882315434756334[35] = 0;
   out_1957882315434756334[36] = 0;
   out_1957882315434756334[37] = 0;
   out_1957882315434756334[38] = 0;
   out_1957882315434756334[39] = 0;
   out_1957882315434756334[40] = 0;
   out_1957882315434756334[41] = 0;
   out_1957882315434756334[42] = 0;
   out_1957882315434756334[43] = 0;
   out_1957882315434756334[44] = 1;
   out_1957882315434756334[45] = 0;
   out_1957882315434756334[46] = 0;
   out_1957882315434756334[47] = 0;
   out_1957882315434756334[48] = 0;
   out_1957882315434756334[49] = 0;
   out_1957882315434756334[50] = 0;
   out_1957882315434756334[51] = 0;
   out_1957882315434756334[52] = 0;
   out_1957882315434756334[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_6769094018143345471) {
  err_fun(nom_x, delta_x, out_6769094018143345471);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7105507959452432978) {
  inv_err_fun(nom_x, true_x, out_7105507959452432978);
}
void pose_H_mod_fun(double *state, double *out_6619985577834044559) {
  H_mod_fun(state, out_6619985577834044559);
}
void pose_f_fun(double *state, double dt, double *out_8911446702564060395) {
  f_fun(state,  dt, out_8911446702564060395);
}
void pose_F_fun(double *state, double dt, double *out_8001086797165012903) {
  F_fun(state,  dt, out_8001086797165012903);
}
void pose_h_4(double *state, double *unused, double *out_700157376215369055) {
  h_4(state, unused, out_700157376215369055);
}
void pose_H_4(double *state, double *unused, double *out_5040670747730128630) {
  H_4(state, unused, out_5040670747730128630);
}
void pose_h_10(double *state, double *unused, double *out_157308656343122283) {
  h_10(state, unused, out_157308656343122283);
}
void pose_H_10(double *state, double *unused, double *out_6282647945703286816) {
  H_10(state, unused, out_6282647945703286816);
}
void pose_h_13(double *state, double *unused, double *out_8562780767398180943) {
  h_13(state, unused, out_8562780767398180943);
}
void pose_H_13(double *state, double *unused, double *out_5795442117662722057) {
  H_13(state, unused, out_5795442117662722057);
}
void pose_h_14(double *state, double *unused, double *out_8175075787359245864) {
  h_14(state, unused, out_8175075787359245864);
}
void pose_H_14(double *state, double *unused, double *out_1957882315434756334) {
  H_14(state, unused, out_1957882315434756334);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
