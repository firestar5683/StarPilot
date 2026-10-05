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
void err_fun(double *nom_x, double *delta_x, double *out_4692908354627516438) {
   out_4692908354627516438[0] = delta_x[0] + nom_x[0];
   out_4692908354627516438[1] = delta_x[1] + nom_x[1];
   out_4692908354627516438[2] = delta_x[2] + nom_x[2];
   out_4692908354627516438[3] = delta_x[3] + nom_x[3];
   out_4692908354627516438[4] = delta_x[4] + nom_x[4];
   out_4692908354627516438[5] = delta_x[5] + nom_x[5];
   out_4692908354627516438[6] = delta_x[6] + nom_x[6];
   out_4692908354627516438[7] = delta_x[7] + nom_x[7];
   out_4692908354627516438[8] = delta_x[8] + nom_x[8];
   out_4692908354627516438[9] = delta_x[9] + nom_x[9];
   out_4692908354627516438[10] = delta_x[10] + nom_x[10];
   out_4692908354627516438[11] = delta_x[11] + nom_x[11];
   out_4692908354627516438[12] = delta_x[12] + nom_x[12];
   out_4692908354627516438[13] = delta_x[13] + nom_x[13];
   out_4692908354627516438[14] = delta_x[14] + nom_x[14];
   out_4692908354627516438[15] = delta_x[15] + nom_x[15];
   out_4692908354627516438[16] = delta_x[16] + nom_x[16];
   out_4692908354627516438[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_4642633870531563233) {
   out_4642633870531563233[0] = -nom_x[0] + true_x[0];
   out_4642633870531563233[1] = -nom_x[1] + true_x[1];
   out_4642633870531563233[2] = -nom_x[2] + true_x[2];
   out_4642633870531563233[3] = -nom_x[3] + true_x[3];
   out_4642633870531563233[4] = -nom_x[4] + true_x[4];
   out_4642633870531563233[5] = -nom_x[5] + true_x[5];
   out_4642633870531563233[6] = -nom_x[6] + true_x[6];
   out_4642633870531563233[7] = -nom_x[7] + true_x[7];
   out_4642633870531563233[8] = -nom_x[8] + true_x[8];
   out_4642633870531563233[9] = -nom_x[9] + true_x[9];
   out_4642633870531563233[10] = -nom_x[10] + true_x[10];
   out_4642633870531563233[11] = -nom_x[11] + true_x[11];
   out_4642633870531563233[12] = -nom_x[12] + true_x[12];
   out_4642633870531563233[13] = -nom_x[13] + true_x[13];
   out_4642633870531563233[14] = -nom_x[14] + true_x[14];
   out_4642633870531563233[15] = -nom_x[15] + true_x[15];
   out_4642633870531563233[16] = -nom_x[16] + true_x[16];
   out_4642633870531563233[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_999051991476226225) {
   out_999051991476226225[0] = 1.0;
   out_999051991476226225[1] = 0.0;
   out_999051991476226225[2] = 0.0;
   out_999051991476226225[3] = 0.0;
   out_999051991476226225[4] = 0.0;
   out_999051991476226225[5] = 0.0;
   out_999051991476226225[6] = 0.0;
   out_999051991476226225[7] = 0.0;
   out_999051991476226225[8] = 0.0;
   out_999051991476226225[9] = 0.0;
   out_999051991476226225[10] = 0.0;
   out_999051991476226225[11] = 0.0;
   out_999051991476226225[12] = 0.0;
   out_999051991476226225[13] = 0.0;
   out_999051991476226225[14] = 0.0;
   out_999051991476226225[15] = 0.0;
   out_999051991476226225[16] = 0.0;
   out_999051991476226225[17] = 0.0;
   out_999051991476226225[18] = 0.0;
   out_999051991476226225[19] = 1.0;
   out_999051991476226225[20] = 0.0;
   out_999051991476226225[21] = 0.0;
   out_999051991476226225[22] = 0.0;
   out_999051991476226225[23] = 0.0;
   out_999051991476226225[24] = 0.0;
   out_999051991476226225[25] = 0.0;
   out_999051991476226225[26] = 0.0;
   out_999051991476226225[27] = 0.0;
   out_999051991476226225[28] = 0.0;
   out_999051991476226225[29] = 0.0;
   out_999051991476226225[30] = 0.0;
   out_999051991476226225[31] = 0.0;
   out_999051991476226225[32] = 0.0;
   out_999051991476226225[33] = 0.0;
   out_999051991476226225[34] = 0.0;
   out_999051991476226225[35] = 0.0;
   out_999051991476226225[36] = 0.0;
   out_999051991476226225[37] = 0.0;
   out_999051991476226225[38] = 1.0;
   out_999051991476226225[39] = 0.0;
   out_999051991476226225[40] = 0.0;
   out_999051991476226225[41] = 0.0;
   out_999051991476226225[42] = 0.0;
   out_999051991476226225[43] = 0.0;
   out_999051991476226225[44] = 0.0;
   out_999051991476226225[45] = 0.0;
   out_999051991476226225[46] = 0.0;
   out_999051991476226225[47] = 0.0;
   out_999051991476226225[48] = 0.0;
   out_999051991476226225[49] = 0.0;
   out_999051991476226225[50] = 0.0;
   out_999051991476226225[51] = 0.0;
   out_999051991476226225[52] = 0.0;
   out_999051991476226225[53] = 0.0;
   out_999051991476226225[54] = 0.0;
   out_999051991476226225[55] = 0.0;
   out_999051991476226225[56] = 0.0;
   out_999051991476226225[57] = 1.0;
   out_999051991476226225[58] = 0.0;
   out_999051991476226225[59] = 0.0;
   out_999051991476226225[60] = 0.0;
   out_999051991476226225[61] = 0.0;
   out_999051991476226225[62] = 0.0;
   out_999051991476226225[63] = 0.0;
   out_999051991476226225[64] = 0.0;
   out_999051991476226225[65] = 0.0;
   out_999051991476226225[66] = 0.0;
   out_999051991476226225[67] = 0.0;
   out_999051991476226225[68] = 0.0;
   out_999051991476226225[69] = 0.0;
   out_999051991476226225[70] = 0.0;
   out_999051991476226225[71] = 0.0;
   out_999051991476226225[72] = 0.0;
   out_999051991476226225[73] = 0.0;
   out_999051991476226225[74] = 0.0;
   out_999051991476226225[75] = 0.0;
   out_999051991476226225[76] = 1.0;
   out_999051991476226225[77] = 0.0;
   out_999051991476226225[78] = 0.0;
   out_999051991476226225[79] = 0.0;
   out_999051991476226225[80] = 0.0;
   out_999051991476226225[81] = 0.0;
   out_999051991476226225[82] = 0.0;
   out_999051991476226225[83] = 0.0;
   out_999051991476226225[84] = 0.0;
   out_999051991476226225[85] = 0.0;
   out_999051991476226225[86] = 0.0;
   out_999051991476226225[87] = 0.0;
   out_999051991476226225[88] = 0.0;
   out_999051991476226225[89] = 0.0;
   out_999051991476226225[90] = 0.0;
   out_999051991476226225[91] = 0.0;
   out_999051991476226225[92] = 0.0;
   out_999051991476226225[93] = 0.0;
   out_999051991476226225[94] = 0.0;
   out_999051991476226225[95] = 1.0;
   out_999051991476226225[96] = 0.0;
   out_999051991476226225[97] = 0.0;
   out_999051991476226225[98] = 0.0;
   out_999051991476226225[99] = 0.0;
   out_999051991476226225[100] = 0.0;
   out_999051991476226225[101] = 0.0;
   out_999051991476226225[102] = 0.0;
   out_999051991476226225[103] = 0.0;
   out_999051991476226225[104] = 0.0;
   out_999051991476226225[105] = 0.0;
   out_999051991476226225[106] = 0.0;
   out_999051991476226225[107] = 0.0;
   out_999051991476226225[108] = 0.0;
   out_999051991476226225[109] = 0.0;
   out_999051991476226225[110] = 0.0;
   out_999051991476226225[111] = 0.0;
   out_999051991476226225[112] = 0.0;
   out_999051991476226225[113] = 0.0;
   out_999051991476226225[114] = 1.0;
   out_999051991476226225[115] = 0.0;
   out_999051991476226225[116] = 0.0;
   out_999051991476226225[117] = 0.0;
   out_999051991476226225[118] = 0.0;
   out_999051991476226225[119] = 0.0;
   out_999051991476226225[120] = 0.0;
   out_999051991476226225[121] = 0.0;
   out_999051991476226225[122] = 0.0;
   out_999051991476226225[123] = 0.0;
   out_999051991476226225[124] = 0.0;
   out_999051991476226225[125] = 0.0;
   out_999051991476226225[126] = 0.0;
   out_999051991476226225[127] = 0.0;
   out_999051991476226225[128] = 0.0;
   out_999051991476226225[129] = 0.0;
   out_999051991476226225[130] = 0.0;
   out_999051991476226225[131] = 0.0;
   out_999051991476226225[132] = 0.0;
   out_999051991476226225[133] = 1.0;
   out_999051991476226225[134] = 0.0;
   out_999051991476226225[135] = 0.0;
   out_999051991476226225[136] = 0.0;
   out_999051991476226225[137] = 0.0;
   out_999051991476226225[138] = 0.0;
   out_999051991476226225[139] = 0.0;
   out_999051991476226225[140] = 0.0;
   out_999051991476226225[141] = 0.0;
   out_999051991476226225[142] = 0.0;
   out_999051991476226225[143] = 0.0;
   out_999051991476226225[144] = 0.0;
   out_999051991476226225[145] = 0.0;
   out_999051991476226225[146] = 0.0;
   out_999051991476226225[147] = 0.0;
   out_999051991476226225[148] = 0.0;
   out_999051991476226225[149] = 0.0;
   out_999051991476226225[150] = 0.0;
   out_999051991476226225[151] = 0.0;
   out_999051991476226225[152] = 1.0;
   out_999051991476226225[153] = 0.0;
   out_999051991476226225[154] = 0.0;
   out_999051991476226225[155] = 0.0;
   out_999051991476226225[156] = 0.0;
   out_999051991476226225[157] = 0.0;
   out_999051991476226225[158] = 0.0;
   out_999051991476226225[159] = 0.0;
   out_999051991476226225[160] = 0.0;
   out_999051991476226225[161] = 0.0;
   out_999051991476226225[162] = 0.0;
   out_999051991476226225[163] = 0.0;
   out_999051991476226225[164] = 0.0;
   out_999051991476226225[165] = 0.0;
   out_999051991476226225[166] = 0.0;
   out_999051991476226225[167] = 0.0;
   out_999051991476226225[168] = 0.0;
   out_999051991476226225[169] = 0.0;
   out_999051991476226225[170] = 0.0;
   out_999051991476226225[171] = 1.0;
   out_999051991476226225[172] = 0.0;
   out_999051991476226225[173] = 0.0;
   out_999051991476226225[174] = 0.0;
   out_999051991476226225[175] = 0.0;
   out_999051991476226225[176] = 0.0;
   out_999051991476226225[177] = 0.0;
   out_999051991476226225[178] = 0.0;
   out_999051991476226225[179] = 0.0;
   out_999051991476226225[180] = 0.0;
   out_999051991476226225[181] = 0.0;
   out_999051991476226225[182] = 0.0;
   out_999051991476226225[183] = 0.0;
   out_999051991476226225[184] = 0.0;
   out_999051991476226225[185] = 0.0;
   out_999051991476226225[186] = 0.0;
   out_999051991476226225[187] = 0.0;
   out_999051991476226225[188] = 0.0;
   out_999051991476226225[189] = 0.0;
   out_999051991476226225[190] = 1.0;
   out_999051991476226225[191] = 0.0;
   out_999051991476226225[192] = 0.0;
   out_999051991476226225[193] = 0.0;
   out_999051991476226225[194] = 0.0;
   out_999051991476226225[195] = 0.0;
   out_999051991476226225[196] = 0.0;
   out_999051991476226225[197] = 0.0;
   out_999051991476226225[198] = 0.0;
   out_999051991476226225[199] = 0.0;
   out_999051991476226225[200] = 0.0;
   out_999051991476226225[201] = 0.0;
   out_999051991476226225[202] = 0.0;
   out_999051991476226225[203] = 0.0;
   out_999051991476226225[204] = 0.0;
   out_999051991476226225[205] = 0.0;
   out_999051991476226225[206] = 0.0;
   out_999051991476226225[207] = 0.0;
   out_999051991476226225[208] = 0.0;
   out_999051991476226225[209] = 1.0;
   out_999051991476226225[210] = 0.0;
   out_999051991476226225[211] = 0.0;
   out_999051991476226225[212] = 0.0;
   out_999051991476226225[213] = 0.0;
   out_999051991476226225[214] = 0.0;
   out_999051991476226225[215] = 0.0;
   out_999051991476226225[216] = 0.0;
   out_999051991476226225[217] = 0.0;
   out_999051991476226225[218] = 0.0;
   out_999051991476226225[219] = 0.0;
   out_999051991476226225[220] = 0.0;
   out_999051991476226225[221] = 0.0;
   out_999051991476226225[222] = 0.0;
   out_999051991476226225[223] = 0.0;
   out_999051991476226225[224] = 0.0;
   out_999051991476226225[225] = 0.0;
   out_999051991476226225[226] = 0.0;
   out_999051991476226225[227] = 0.0;
   out_999051991476226225[228] = 1.0;
   out_999051991476226225[229] = 0.0;
   out_999051991476226225[230] = 0.0;
   out_999051991476226225[231] = 0.0;
   out_999051991476226225[232] = 0.0;
   out_999051991476226225[233] = 0.0;
   out_999051991476226225[234] = 0.0;
   out_999051991476226225[235] = 0.0;
   out_999051991476226225[236] = 0.0;
   out_999051991476226225[237] = 0.0;
   out_999051991476226225[238] = 0.0;
   out_999051991476226225[239] = 0.0;
   out_999051991476226225[240] = 0.0;
   out_999051991476226225[241] = 0.0;
   out_999051991476226225[242] = 0.0;
   out_999051991476226225[243] = 0.0;
   out_999051991476226225[244] = 0.0;
   out_999051991476226225[245] = 0.0;
   out_999051991476226225[246] = 0.0;
   out_999051991476226225[247] = 1.0;
   out_999051991476226225[248] = 0.0;
   out_999051991476226225[249] = 0.0;
   out_999051991476226225[250] = 0.0;
   out_999051991476226225[251] = 0.0;
   out_999051991476226225[252] = 0.0;
   out_999051991476226225[253] = 0.0;
   out_999051991476226225[254] = 0.0;
   out_999051991476226225[255] = 0.0;
   out_999051991476226225[256] = 0.0;
   out_999051991476226225[257] = 0.0;
   out_999051991476226225[258] = 0.0;
   out_999051991476226225[259] = 0.0;
   out_999051991476226225[260] = 0.0;
   out_999051991476226225[261] = 0.0;
   out_999051991476226225[262] = 0.0;
   out_999051991476226225[263] = 0.0;
   out_999051991476226225[264] = 0.0;
   out_999051991476226225[265] = 0.0;
   out_999051991476226225[266] = 1.0;
   out_999051991476226225[267] = 0.0;
   out_999051991476226225[268] = 0.0;
   out_999051991476226225[269] = 0.0;
   out_999051991476226225[270] = 0.0;
   out_999051991476226225[271] = 0.0;
   out_999051991476226225[272] = 0.0;
   out_999051991476226225[273] = 0.0;
   out_999051991476226225[274] = 0.0;
   out_999051991476226225[275] = 0.0;
   out_999051991476226225[276] = 0.0;
   out_999051991476226225[277] = 0.0;
   out_999051991476226225[278] = 0.0;
   out_999051991476226225[279] = 0.0;
   out_999051991476226225[280] = 0.0;
   out_999051991476226225[281] = 0.0;
   out_999051991476226225[282] = 0.0;
   out_999051991476226225[283] = 0.0;
   out_999051991476226225[284] = 0.0;
   out_999051991476226225[285] = 1.0;
   out_999051991476226225[286] = 0.0;
   out_999051991476226225[287] = 0.0;
   out_999051991476226225[288] = 0.0;
   out_999051991476226225[289] = 0.0;
   out_999051991476226225[290] = 0.0;
   out_999051991476226225[291] = 0.0;
   out_999051991476226225[292] = 0.0;
   out_999051991476226225[293] = 0.0;
   out_999051991476226225[294] = 0.0;
   out_999051991476226225[295] = 0.0;
   out_999051991476226225[296] = 0.0;
   out_999051991476226225[297] = 0.0;
   out_999051991476226225[298] = 0.0;
   out_999051991476226225[299] = 0.0;
   out_999051991476226225[300] = 0.0;
   out_999051991476226225[301] = 0.0;
   out_999051991476226225[302] = 0.0;
   out_999051991476226225[303] = 0.0;
   out_999051991476226225[304] = 1.0;
   out_999051991476226225[305] = 0.0;
   out_999051991476226225[306] = 0.0;
   out_999051991476226225[307] = 0.0;
   out_999051991476226225[308] = 0.0;
   out_999051991476226225[309] = 0.0;
   out_999051991476226225[310] = 0.0;
   out_999051991476226225[311] = 0.0;
   out_999051991476226225[312] = 0.0;
   out_999051991476226225[313] = 0.0;
   out_999051991476226225[314] = 0.0;
   out_999051991476226225[315] = 0.0;
   out_999051991476226225[316] = 0.0;
   out_999051991476226225[317] = 0.0;
   out_999051991476226225[318] = 0.0;
   out_999051991476226225[319] = 0.0;
   out_999051991476226225[320] = 0.0;
   out_999051991476226225[321] = 0.0;
   out_999051991476226225[322] = 0.0;
   out_999051991476226225[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8595496590093260126) {
   out_8595496590093260126[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8595496590093260126[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8595496590093260126[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8595496590093260126[3] = dt*state[12] + state[3];
   out_8595496590093260126[4] = dt*state[13] + state[4];
   out_8595496590093260126[5] = dt*state[14] + state[5];
   out_8595496590093260126[6] = state[6];
   out_8595496590093260126[7] = state[7];
   out_8595496590093260126[8] = state[8];
   out_8595496590093260126[9] = state[9];
   out_8595496590093260126[10] = state[10];
   out_8595496590093260126[11] = state[11];
   out_8595496590093260126[12] = state[12];
   out_8595496590093260126[13] = state[13];
   out_8595496590093260126[14] = state[14];
   out_8595496590093260126[15] = state[15];
   out_8595496590093260126[16] = state[16];
   out_8595496590093260126[17] = state[17];
}
void F_fun(double *state, double dt, double *out_600705311639882547) {
   out_600705311639882547[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_600705311639882547[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_600705311639882547[2] = 0;
   out_600705311639882547[3] = 0;
   out_600705311639882547[4] = 0;
   out_600705311639882547[5] = 0;
   out_600705311639882547[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_600705311639882547[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_600705311639882547[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_600705311639882547[9] = 0;
   out_600705311639882547[10] = 0;
   out_600705311639882547[11] = 0;
   out_600705311639882547[12] = 0;
   out_600705311639882547[13] = 0;
   out_600705311639882547[14] = 0;
   out_600705311639882547[15] = 0;
   out_600705311639882547[16] = 0;
   out_600705311639882547[17] = 0;
   out_600705311639882547[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_600705311639882547[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_600705311639882547[20] = 0;
   out_600705311639882547[21] = 0;
   out_600705311639882547[22] = 0;
   out_600705311639882547[23] = 0;
   out_600705311639882547[24] = 0;
   out_600705311639882547[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_600705311639882547[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_600705311639882547[27] = 0;
   out_600705311639882547[28] = 0;
   out_600705311639882547[29] = 0;
   out_600705311639882547[30] = 0;
   out_600705311639882547[31] = 0;
   out_600705311639882547[32] = 0;
   out_600705311639882547[33] = 0;
   out_600705311639882547[34] = 0;
   out_600705311639882547[35] = 0;
   out_600705311639882547[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_600705311639882547[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_600705311639882547[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_600705311639882547[39] = 0;
   out_600705311639882547[40] = 0;
   out_600705311639882547[41] = 0;
   out_600705311639882547[42] = 0;
   out_600705311639882547[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_600705311639882547[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_600705311639882547[45] = 0;
   out_600705311639882547[46] = 0;
   out_600705311639882547[47] = 0;
   out_600705311639882547[48] = 0;
   out_600705311639882547[49] = 0;
   out_600705311639882547[50] = 0;
   out_600705311639882547[51] = 0;
   out_600705311639882547[52] = 0;
   out_600705311639882547[53] = 0;
   out_600705311639882547[54] = 0;
   out_600705311639882547[55] = 0;
   out_600705311639882547[56] = 0;
   out_600705311639882547[57] = 1;
   out_600705311639882547[58] = 0;
   out_600705311639882547[59] = 0;
   out_600705311639882547[60] = 0;
   out_600705311639882547[61] = 0;
   out_600705311639882547[62] = 0;
   out_600705311639882547[63] = 0;
   out_600705311639882547[64] = 0;
   out_600705311639882547[65] = 0;
   out_600705311639882547[66] = dt;
   out_600705311639882547[67] = 0;
   out_600705311639882547[68] = 0;
   out_600705311639882547[69] = 0;
   out_600705311639882547[70] = 0;
   out_600705311639882547[71] = 0;
   out_600705311639882547[72] = 0;
   out_600705311639882547[73] = 0;
   out_600705311639882547[74] = 0;
   out_600705311639882547[75] = 0;
   out_600705311639882547[76] = 1;
   out_600705311639882547[77] = 0;
   out_600705311639882547[78] = 0;
   out_600705311639882547[79] = 0;
   out_600705311639882547[80] = 0;
   out_600705311639882547[81] = 0;
   out_600705311639882547[82] = 0;
   out_600705311639882547[83] = 0;
   out_600705311639882547[84] = 0;
   out_600705311639882547[85] = dt;
   out_600705311639882547[86] = 0;
   out_600705311639882547[87] = 0;
   out_600705311639882547[88] = 0;
   out_600705311639882547[89] = 0;
   out_600705311639882547[90] = 0;
   out_600705311639882547[91] = 0;
   out_600705311639882547[92] = 0;
   out_600705311639882547[93] = 0;
   out_600705311639882547[94] = 0;
   out_600705311639882547[95] = 1;
   out_600705311639882547[96] = 0;
   out_600705311639882547[97] = 0;
   out_600705311639882547[98] = 0;
   out_600705311639882547[99] = 0;
   out_600705311639882547[100] = 0;
   out_600705311639882547[101] = 0;
   out_600705311639882547[102] = 0;
   out_600705311639882547[103] = 0;
   out_600705311639882547[104] = dt;
   out_600705311639882547[105] = 0;
   out_600705311639882547[106] = 0;
   out_600705311639882547[107] = 0;
   out_600705311639882547[108] = 0;
   out_600705311639882547[109] = 0;
   out_600705311639882547[110] = 0;
   out_600705311639882547[111] = 0;
   out_600705311639882547[112] = 0;
   out_600705311639882547[113] = 0;
   out_600705311639882547[114] = 1;
   out_600705311639882547[115] = 0;
   out_600705311639882547[116] = 0;
   out_600705311639882547[117] = 0;
   out_600705311639882547[118] = 0;
   out_600705311639882547[119] = 0;
   out_600705311639882547[120] = 0;
   out_600705311639882547[121] = 0;
   out_600705311639882547[122] = 0;
   out_600705311639882547[123] = 0;
   out_600705311639882547[124] = 0;
   out_600705311639882547[125] = 0;
   out_600705311639882547[126] = 0;
   out_600705311639882547[127] = 0;
   out_600705311639882547[128] = 0;
   out_600705311639882547[129] = 0;
   out_600705311639882547[130] = 0;
   out_600705311639882547[131] = 0;
   out_600705311639882547[132] = 0;
   out_600705311639882547[133] = 1;
   out_600705311639882547[134] = 0;
   out_600705311639882547[135] = 0;
   out_600705311639882547[136] = 0;
   out_600705311639882547[137] = 0;
   out_600705311639882547[138] = 0;
   out_600705311639882547[139] = 0;
   out_600705311639882547[140] = 0;
   out_600705311639882547[141] = 0;
   out_600705311639882547[142] = 0;
   out_600705311639882547[143] = 0;
   out_600705311639882547[144] = 0;
   out_600705311639882547[145] = 0;
   out_600705311639882547[146] = 0;
   out_600705311639882547[147] = 0;
   out_600705311639882547[148] = 0;
   out_600705311639882547[149] = 0;
   out_600705311639882547[150] = 0;
   out_600705311639882547[151] = 0;
   out_600705311639882547[152] = 1;
   out_600705311639882547[153] = 0;
   out_600705311639882547[154] = 0;
   out_600705311639882547[155] = 0;
   out_600705311639882547[156] = 0;
   out_600705311639882547[157] = 0;
   out_600705311639882547[158] = 0;
   out_600705311639882547[159] = 0;
   out_600705311639882547[160] = 0;
   out_600705311639882547[161] = 0;
   out_600705311639882547[162] = 0;
   out_600705311639882547[163] = 0;
   out_600705311639882547[164] = 0;
   out_600705311639882547[165] = 0;
   out_600705311639882547[166] = 0;
   out_600705311639882547[167] = 0;
   out_600705311639882547[168] = 0;
   out_600705311639882547[169] = 0;
   out_600705311639882547[170] = 0;
   out_600705311639882547[171] = 1;
   out_600705311639882547[172] = 0;
   out_600705311639882547[173] = 0;
   out_600705311639882547[174] = 0;
   out_600705311639882547[175] = 0;
   out_600705311639882547[176] = 0;
   out_600705311639882547[177] = 0;
   out_600705311639882547[178] = 0;
   out_600705311639882547[179] = 0;
   out_600705311639882547[180] = 0;
   out_600705311639882547[181] = 0;
   out_600705311639882547[182] = 0;
   out_600705311639882547[183] = 0;
   out_600705311639882547[184] = 0;
   out_600705311639882547[185] = 0;
   out_600705311639882547[186] = 0;
   out_600705311639882547[187] = 0;
   out_600705311639882547[188] = 0;
   out_600705311639882547[189] = 0;
   out_600705311639882547[190] = 1;
   out_600705311639882547[191] = 0;
   out_600705311639882547[192] = 0;
   out_600705311639882547[193] = 0;
   out_600705311639882547[194] = 0;
   out_600705311639882547[195] = 0;
   out_600705311639882547[196] = 0;
   out_600705311639882547[197] = 0;
   out_600705311639882547[198] = 0;
   out_600705311639882547[199] = 0;
   out_600705311639882547[200] = 0;
   out_600705311639882547[201] = 0;
   out_600705311639882547[202] = 0;
   out_600705311639882547[203] = 0;
   out_600705311639882547[204] = 0;
   out_600705311639882547[205] = 0;
   out_600705311639882547[206] = 0;
   out_600705311639882547[207] = 0;
   out_600705311639882547[208] = 0;
   out_600705311639882547[209] = 1;
   out_600705311639882547[210] = 0;
   out_600705311639882547[211] = 0;
   out_600705311639882547[212] = 0;
   out_600705311639882547[213] = 0;
   out_600705311639882547[214] = 0;
   out_600705311639882547[215] = 0;
   out_600705311639882547[216] = 0;
   out_600705311639882547[217] = 0;
   out_600705311639882547[218] = 0;
   out_600705311639882547[219] = 0;
   out_600705311639882547[220] = 0;
   out_600705311639882547[221] = 0;
   out_600705311639882547[222] = 0;
   out_600705311639882547[223] = 0;
   out_600705311639882547[224] = 0;
   out_600705311639882547[225] = 0;
   out_600705311639882547[226] = 0;
   out_600705311639882547[227] = 0;
   out_600705311639882547[228] = 1;
   out_600705311639882547[229] = 0;
   out_600705311639882547[230] = 0;
   out_600705311639882547[231] = 0;
   out_600705311639882547[232] = 0;
   out_600705311639882547[233] = 0;
   out_600705311639882547[234] = 0;
   out_600705311639882547[235] = 0;
   out_600705311639882547[236] = 0;
   out_600705311639882547[237] = 0;
   out_600705311639882547[238] = 0;
   out_600705311639882547[239] = 0;
   out_600705311639882547[240] = 0;
   out_600705311639882547[241] = 0;
   out_600705311639882547[242] = 0;
   out_600705311639882547[243] = 0;
   out_600705311639882547[244] = 0;
   out_600705311639882547[245] = 0;
   out_600705311639882547[246] = 0;
   out_600705311639882547[247] = 1;
   out_600705311639882547[248] = 0;
   out_600705311639882547[249] = 0;
   out_600705311639882547[250] = 0;
   out_600705311639882547[251] = 0;
   out_600705311639882547[252] = 0;
   out_600705311639882547[253] = 0;
   out_600705311639882547[254] = 0;
   out_600705311639882547[255] = 0;
   out_600705311639882547[256] = 0;
   out_600705311639882547[257] = 0;
   out_600705311639882547[258] = 0;
   out_600705311639882547[259] = 0;
   out_600705311639882547[260] = 0;
   out_600705311639882547[261] = 0;
   out_600705311639882547[262] = 0;
   out_600705311639882547[263] = 0;
   out_600705311639882547[264] = 0;
   out_600705311639882547[265] = 0;
   out_600705311639882547[266] = 1;
   out_600705311639882547[267] = 0;
   out_600705311639882547[268] = 0;
   out_600705311639882547[269] = 0;
   out_600705311639882547[270] = 0;
   out_600705311639882547[271] = 0;
   out_600705311639882547[272] = 0;
   out_600705311639882547[273] = 0;
   out_600705311639882547[274] = 0;
   out_600705311639882547[275] = 0;
   out_600705311639882547[276] = 0;
   out_600705311639882547[277] = 0;
   out_600705311639882547[278] = 0;
   out_600705311639882547[279] = 0;
   out_600705311639882547[280] = 0;
   out_600705311639882547[281] = 0;
   out_600705311639882547[282] = 0;
   out_600705311639882547[283] = 0;
   out_600705311639882547[284] = 0;
   out_600705311639882547[285] = 1;
   out_600705311639882547[286] = 0;
   out_600705311639882547[287] = 0;
   out_600705311639882547[288] = 0;
   out_600705311639882547[289] = 0;
   out_600705311639882547[290] = 0;
   out_600705311639882547[291] = 0;
   out_600705311639882547[292] = 0;
   out_600705311639882547[293] = 0;
   out_600705311639882547[294] = 0;
   out_600705311639882547[295] = 0;
   out_600705311639882547[296] = 0;
   out_600705311639882547[297] = 0;
   out_600705311639882547[298] = 0;
   out_600705311639882547[299] = 0;
   out_600705311639882547[300] = 0;
   out_600705311639882547[301] = 0;
   out_600705311639882547[302] = 0;
   out_600705311639882547[303] = 0;
   out_600705311639882547[304] = 1;
   out_600705311639882547[305] = 0;
   out_600705311639882547[306] = 0;
   out_600705311639882547[307] = 0;
   out_600705311639882547[308] = 0;
   out_600705311639882547[309] = 0;
   out_600705311639882547[310] = 0;
   out_600705311639882547[311] = 0;
   out_600705311639882547[312] = 0;
   out_600705311639882547[313] = 0;
   out_600705311639882547[314] = 0;
   out_600705311639882547[315] = 0;
   out_600705311639882547[316] = 0;
   out_600705311639882547[317] = 0;
   out_600705311639882547[318] = 0;
   out_600705311639882547[319] = 0;
   out_600705311639882547[320] = 0;
   out_600705311639882547[321] = 0;
   out_600705311639882547[322] = 0;
   out_600705311639882547[323] = 1;
}
void h_4(double *state, double *unused, double *out_2786040394933084983) {
   out_2786040394933084983[0] = state[6] + state[9];
   out_2786040394933084983[1] = state[7] + state[10];
   out_2786040394933084983[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_1531113305230126453) {
   out_1531113305230126453[0] = 0;
   out_1531113305230126453[1] = 0;
   out_1531113305230126453[2] = 0;
   out_1531113305230126453[3] = 0;
   out_1531113305230126453[4] = 0;
   out_1531113305230126453[5] = 0;
   out_1531113305230126453[6] = 1;
   out_1531113305230126453[7] = 0;
   out_1531113305230126453[8] = 0;
   out_1531113305230126453[9] = 1;
   out_1531113305230126453[10] = 0;
   out_1531113305230126453[11] = 0;
   out_1531113305230126453[12] = 0;
   out_1531113305230126453[13] = 0;
   out_1531113305230126453[14] = 0;
   out_1531113305230126453[15] = 0;
   out_1531113305230126453[16] = 0;
   out_1531113305230126453[17] = 0;
   out_1531113305230126453[18] = 0;
   out_1531113305230126453[19] = 0;
   out_1531113305230126453[20] = 0;
   out_1531113305230126453[21] = 0;
   out_1531113305230126453[22] = 0;
   out_1531113305230126453[23] = 0;
   out_1531113305230126453[24] = 0;
   out_1531113305230126453[25] = 1;
   out_1531113305230126453[26] = 0;
   out_1531113305230126453[27] = 0;
   out_1531113305230126453[28] = 1;
   out_1531113305230126453[29] = 0;
   out_1531113305230126453[30] = 0;
   out_1531113305230126453[31] = 0;
   out_1531113305230126453[32] = 0;
   out_1531113305230126453[33] = 0;
   out_1531113305230126453[34] = 0;
   out_1531113305230126453[35] = 0;
   out_1531113305230126453[36] = 0;
   out_1531113305230126453[37] = 0;
   out_1531113305230126453[38] = 0;
   out_1531113305230126453[39] = 0;
   out_1531113305230126453[40] = 0;
   out_1531113305230126453[41] = 0;
   out_1531113305230126453[42] = 0;
   out_1531113305230126453[43] = 0;
   out_1531113305230126453[44] = 1;
   out_1531113305230126453[45] = 0;
   out_1531113305230126453[46] = 0;
   out_1531113305230126453[47] = 1;
   out_1531113305230126453[48] = 0;
   out_1531113305230126453[49] = 0;
   out_1531113305230126453[50] = 0;
   out_1531113305230126453[51] = 0;
   out_1531113305230126453[52] = 0;
   out_1531113305230126453[53] = 0;
}
void h_10(double *state, double *unused, double *out_2868077015136456598) {
   out_2868077015136456598[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_2868077015136456598[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_2868077015136456598[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_3113914393471003549) {
   out_3113914393471003549[0] = 0;
   out_3113914393471003549[1] = 9.8100000000000005*cos(state[1]);
   out_3113914393471003549[2] = 0;
   out_3113914393471003549[3] = 0;
   out_3113914393471003549[4] = -state[8];
   out_3113914393471003549[5] = state[7];
   out_3113914393471003549[6] = 0;
   out_3113914393471003549[7] = state[5];
   out_3113914393471003549[8] = -state[4];
   out_3113914393471003549[9] = 0;
   out_3113914393471003549[10] = 0;
   out_3113914393471003549[11] = 0;
   out_3113914393471003549[12] = 1;
   out_3113914393471003549[13] = 0;
   out_3113914393471003549[14] = 0;
   out_3113914393471003549[15] = 1;
   out_3113914393471003549[16] = 0;
   out_3113914393471003549[17] = 0;
   out_3113914393471003549[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_3113914393471003549[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_3113914393471003549[20] = 0;
   out_3113914393471003549[21] = state[8];
   out_3113914393471003549[22] = 0;
   out_3113914393471003549[23] = -state[6];
   out_3113914393471003549[24] = -state[5];
   out_3113914393471003549[25] = 0;
   out_3113914393471003549[26] = state[3];
   out_3113914393471003549[27] = 0;
   out_3113914393471003549[28] = 0;
   out_3113914393471003549[29] = 0;
   out_3113914393471003549[30] = 0;
   out_3113914393471003549[31] = 1;
   out_3113914393471003549[32] = 0;
   out_3113914393471003549[33] = 0;
   out_3113914393471003549[34] = 1;
   out_3113914393471003549[35] = 0;
   out_3113914393471003549[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_3113914393471003549[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_3113914393471003549[38] = 0;
   out_3113914393471003549[39] = -state[7];
   out_3113914393471003549[40] = state[6];
   out_3113914393471003549[41] = 0;
   out_3113914393471003549[42] = state[4];
   out_3113914393471003549[43] = -state[3];
   out_3113914393471003549[44] = 0;
   out_3113914393471003549[45] = 0;
   out_3113914393471003549[46] = 0;
   out_3113914393471003549[47] = 0;
   out_3113914393471003549[48] = 0;
   out_3113914393471003549[49] = 0;
   out_3113914393471003549[50] = 1;
   out_3113914393471003549[51] = 0;
   out_3113914393471003549[52] = 0;
   out_3113914393471003549[53] = 1;
}
void h_13(double *state, double *unused, double *out_3137887318351603650) {
   out_3137887318351603650[0] = state[3];
   out_3137887318351603650[1] = state[4];
   out_3137887318351603650[2] = state[5];
}
void H_13(double *state, double *unused, double *out_2095715224911970557) {
   out_2095715224911970557[0] = 0;
   out_2095715224911970557[1] = 0;
   out_2095715224911970557[2] = 0;
   out_2095715224911970557[3] = 1;
   out_2095715224911970557[4] = 0;
   out_2095715224911970557[5] = 0;
   out_2095715224911970557[6] = 0;
   out_2095715224911970557[7] = 0;
   out_2095715224911970557[8] = 0;
   out_2095715224911970557[9] = 0;
   out_2095715224911970557[10] = 0;
   out_2095715224911970557[11] = 0;
   out_2095715224911970557[12] = 0;
   out_2095715224911970557[13] = 0;
   out_2095715224911970557[14] = 0;
   out_2095715224911970557[15] = 0;
   out_2095715224911970557[16] = 0;
   out_2095715224911970557[17] = 0;
   out_2095715224911970557[18] = 0;
   out_2095715224911970557[19] = 0;
   out_2095715224911970557[20] = 0;
   out_2095715224911970557[21] = 0;
   out_2095715224911970557[22] = 1;
   out_2095715224911970557[23] = 0;
   out_2095715224911970557[24] = 0;
   out_2095715224911970557[25] = 0;
   out_2095715224911970557[26] = 0;
   out_2095715224911970557[27] = 0;
   out_2095715224911970557[28] = 0;
   out_2095715224911970557[29] = 0;
   out_2095715224911970557[30] = 0;
   out_2095715224911970557[31] = 0;
   out_2095715224911970557[32] = 0;
   out_2095715224911970557[33] = 0;
   out_2095715224911970557[34] = 0;
   out_2095715224911970557[35] = 0;
   out_2095715224911970557[36] = 0;
   out_2095715224911970557[37] = 0;
   out_2095715224911970557[38] = 0;
   out_2095715224911970557[39] = 0;
   out_2095715224911970557[40] = 0;
   out_2095715224911970557[41] = 1;
   out_2095715224911970557[42] = 0;
   out_2095715224911970557[43] = 0;
   out_2095715224911970557[44] = 0;
   out_2095715224911970557[45] = 0;
   out_2095715224911970557[46] = 0;
   out_2095715224911970557[47] = 0;
   out_2095715224911970557[48] = 0;
   out_2095715224911970557[49] = 0;
   out_2095715224911970557[50] = 0;
   out_2095715224911970557[51] = 0;
   out_2095715224911970557[52] = 0;
   out_2095715224911970557[53] = 0;
}
void h_14(double *state, double *unused, double *out_6370524001895544374) {
   out_6370524001895544374[0] = state[6];
   out_6370524001895544374[1] = state[7];
   out_6370524001895544374[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1551675127065245843) {
   out_1551675127065245843[0] = 0;
   out_1551675127065245843[1] = 0;
   out_1551675127065245843[2] = 0;
   out_1551675127065245843[3] = 0;
   out_1551675127065245843[4] = 0;
   out_1551675127065245843[5] = 0;
   out_1551675127065245843[6] = 1;
   out_1551675127065245843[7] = 0;
   out_1551675127065245843[8] = 0;
   out_1551675127065245843[9] = 0;
   out_1551675127065245843[10] = 0;
   out_1551675127065245843[11] = 0;
   out_1551675127065245843[12] = 0;
   out_1551675127065245843[13] = 0;
   out_1551675127065245843[14] = 0;
   out_1551675127065245843[15] = 0;
   out_1551675127065245843[16] = 0;
   out_1551675127065245843[17] = 0;
   out_1551675127065245843[18] = 0;
   out_1551675127065245843[19] = 0;
   out_1551675127065245843[20] = 0;
   out_1551675127065245843[21] = 0;
   out_1551675127065245843[22] = 0;
   out_1551675127065245843[23] = 0;
   out_1551675127065245843[24] = 0;
   out_1551675127065245843[25] = 1;
   out_1551675127065245843[26] = 0;
   out_1551675127065245843[27] = 0;
   out_1551675127065245843[28] = 0;
   out_1551675127065245843[29] = 0;
   out_1551675127065245843[30] = 0;
   out_1551675127065245843[31] = 0;
   out_1551675127065245843[32] = 0;
   out_1551675127065245843[33] = 0;
   out_1551675127065245843[34] = 0;
   out_1551675127065245843[35] = 0;
   out_1551675127065245843[36] = 0;
   out_1551675127065245843[37] = 0;
   out_1551675127065245843[38] = 0;
   out_1551675127065245843[39] = 0;
   out_1551675127065245843[40] = 0;
   out_1551675127065245843[41] = 0;
   out_1551675127065245843[42] = 0;
   out_1551675127065245843[43] = 0;
   out_1551675127065245843[44] = 1;
   out_1551675127065245843[45] = 0;
   out_1551675127065245843[46] = 0;
   out_1551675127065245843[47] = 0;
   out_1551675127065245843[48] = 0;
   out_1551675127065245843[49] = 0;
   out_1551675127065245843[50] = 0;
   out_1551675127065245843[51] = 0;
   out_1551675127065245843[52] = 0;
   out_1551675127065245843[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_4692908354627516438) {
  err_fun(nom_x, delta_x, out_4692908354627516438);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_4642633870531563233) {
  inv_err_fun(nom_x, true_x, out_4642633870531563233);
}
void pose_H_mod_fun(double *state, double *out_999051991476226225) {
  H_mod_fun(state, out_999051991476226225);
}
void pose_f_fun(double *state, double dt, double *out_8595496590093260126) {
  f_fun(state,  dt, out_8595496590093260126);
}
void pose_F_fun(double *state, double dt, double *out_600705311639882547) {
  F_fun(state,  dt, out_600705311639882547);
}
void pose_h_4(double *state, double *unused, double *out_2786040394933084983) {
  h_4(state, unused, out_2786040394933084983);
}
void pose_H_4(double *state, double *unused, double *out_1531113305230126453) {
  H_4(state, unused, out_1531113305230126453);
}
void pose_h_10(double *state, double *unused, double *out_2868077015136456598) {
  h_10(state, unused, out_2868077015136456598);
}
void pose_H_10(double *state, double *unused, double *out_3113914393471003549) {
  H_10(state, unused, out_3113914393471003549);
}
void pose_h_13(double *state, double *unused, double *out_3137887318351603650) {
  h_13(state, unused, out_3137887318351603650);
}
void pose_H_13(double *state, double *unused, double *out_2095715224911970557) {
  H_13(state, unused, out_2095715224911970557);
}
void pose_h_14(double *state, double *unused, double *out_6370524001895544374) {
  h_14(state, unused, out_6370524001895544374);
}
void pose_H_14(double *state, double *unused, double *out_1551675127065245843) {
  H_14(state, unused, out_1551675127065245843);
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
