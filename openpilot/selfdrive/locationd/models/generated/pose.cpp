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
void err_fun(double *nom_x, double *delta_x, double *out_1002597543094682529) {
   out_1002597543094682529[0] = delta_x[0] + nom_x[0];
   out_1002597543094682529[1] = delta_x[1] + nom_x[1];
   out_1002597543094682529[2] = delta_x[2] + nom_x[2];
   out_1002597543094682529[3] = delta_x[3] + nom_x[3];
   out_1002597543094682529[4] = delta_x[4] + nom_x[4];
   out_1002597543094682529[5] = delta_x[5] + nom_x[5];
   out_1002597543094682529[6] = delta_x[6] + nom_x[6];
   out_1002597543094682529[7] = delta_x[7] + nom_x[7];
   out_1002597543094682529[8] = delta_x[8] + nom_x[8];
   out_1002597543094682529[9] = delta_x[9] + nom_x[9];
   out_1002597543094682529[10] = delta_x[10] + nom_x[10];
   out_1002597543094682529[11] = delta_x[11] + nom_x[11];
   out_1002597543094682529[12] = delta_x[12] + nom_x[12];
   out_1002597543094682529[13] = delta_x[13] + nom_x[13];
   out_1002597543094682529[14] = delta_x[14] + nom_x[14];
   out_1002597543094682529[15] = delta_x[15] + nom_x[15];
   out_1002597543094682529[16] = delta_x[16] + nom_x[16];
   out_1002597543094682529[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6790221310632921126) {
   out_6790221310632921126[0] = -nom_x[0] + true_x[0];
   out_6790221310632921126[1] = -nom_x[1] + true_x[1];
   out_6790221310632921126[2] = -nom_x[2] + true_x[2];
   out_6790221310632921126[3] = -nom_x[3] + true_x[3];
   out_6790221310632921126[4] = -nom_x[4] + true_x[4];
   out_6790221310632921126[5] = -nom_x[5] + true_x[5];
   out_6790221310632921126[6] = -nom_x[6] + true_x[6];
   out_6790221310632921126[7] = -nom_x[7] + true_x[7];
   out_6790221310632921126[8] = -nom_x[8] + true_x[8];
   out_6790221310632921126[9] = -nom_x[9] + true_x[9];
   out_6790221310632921126[10] = -nom_x[10] + true_x[10];
   out_6790221310632921126[11] = -nom_x[11] + true_x[11];
   out_6790221310632921126[12] = -nom_x[12] + true_x[12];
   out_6790221310632921126[13] = -nom_x[13] + true_x[13];
   out_6790221310632921126[14] = -nom_x[14] + true_x[14];
   out_6790221310632921126[15] = -nom_x[15] + true_x[15];
   out_6790221310632921126[16] = -nom_x[16] + true_x[16];
   out_6790221310632921126[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_1061940044083541431) {
   out_1061940044083541431[0] = 1.0;
   out_1061940044083541431[1] = 0.0;
   out_1061940044083541431[2] = 0.0;
   out_1061940044083541431[3] = 0.0;
   out_1061940044083541431[4] = 0.0;
   out_1061940044083541431[5] = 0.0;
   out_1061940044083541431[6] = 0.0;
   out_1061940044083541431[7] = 0.0;
   out_1061940044083541431[8] = 0.0;
   out_1061940044083541431[9] = 0.0;
   out_1061940044083541431[10] = 0.0;
   out_1061940044083541431[11] = 0.0;
   out_1061940044083541431[12] = 0.0;
   out_1061940044083541431[13] = 0.0;
   out_1061940044083541431[14] = 0.0;
   out_1061940044083541431[15] = 0.0;
   out_1061940044083541431[16] = 0.0;
   out_1061940044083541431[17] = 0.0;
   out_1061940044083541431[18] = 0.0;
   out_1061940044083541431[19] = 1.0;
   out_1061940044083541431[20] = 0.0;
   out_1061940044083541431[21] = 0.0;
   out_1061940044083541431[22] = 0.0;
   out_1061940044083541431[23] = 0.0;
   out_1061940044083541431[24] = 0.0;
   out_1061940044083541431[25] = 0.0;
   out_1061940044083541431[26] = 0.0;
   out_1061940044083541431[27] = 0.0;
   out_1061940044083541431[28] = 0.0;
   out_1061940044083541431[29] = 0.0;
   out_1061940044083541431[30] = 0.0;
   out_1061940044083541431[31] = 0.0;
   out_1061940044083541431[32] = 0.0;
   out_1061940044083541431[33] = 0.0;
   out_1061940044083541431[34] = 0.0;
   out_1061940044083541431[35] = 0.0;
   out_1061940044083541431[36] = 0.0;
   out_1061940044083541431[37] = 0.0;
   out_1061940044083541431[38] = 1.0;
   out_1061940044083541431[39] = 0.0;
   out_1061940044083541431[40] = 0.0;
   out_1061940044083541431[41] = 0.0;
   out_1061940044083541431[42] = 0.0;
   out_1061940044083541431[43] = 0.0;
   out_1061940044083541431[44] = 0.0;
   out_1061940044083541431[45] = 0.0;
   out_1061940044083541431[46] = 0.0;
   out_1061940044083541431[47] = 0.0;
   out_1061940044083541431[48] = 0.0;
   out_1061940044083541431[49] = 0.0;
   out_1061940044083541431[50] = 0.0;
   out_1061940044083541431[51] = 0.0;
   out_1061940044083541431[52] = 0.0;
   out_1061940044083541431[53] = 0.0;
   out_1061940044083541431[54] = 0.0;
   out_1061940044083541431[55] = 0.0;
   out_1061940044083541431[56] = 0.0;
   out_1061940044083541431[57] = 1.0;
   out_1061940044083541431[58] = 0.0;
   out_1061940044083541431[59] = 0.0;
   out_1061940044083541431[60] = 0.0;
   out_1061940044083541431[61] = 0.0;
   out_1061940044083541431[62] = 0.0;
   out_1061940044083541431[63] = 0.0;
   out_1061940044083541431[64] = 0.0;
   out_1061940044083541431[65] = 0.0;
   out_1061940044083541431[66] = 0.0;
   out_1061940044083541431[67] = 0.0;
   out_1061940044083541431[68] = 0.0;
   out_1061940044083541431[69] = 0.0;
   out_1061940044083541431[70] = 0.0;
   out_1061940044083541431[71] = 0.0;
   out_1061940044083541431[72] = 0.0;
   out_1061940044083541431[73] = 0.0;
   out_1061940044083541431[74] = 0.0;
   out_1061940044083541431[75] = 0.0;
   out_1061940044083541431[76] = 1.0;
   out_1061940044083541431[77] = 0.0;
   out_1061940044083541431[78] = 0.0;
   out_1061940044083541431[79] = 0.0;
   out_1061940044083541431[80] = 0.0;
   out_1061940044083541431[81] = 0.0;
   out_1061940044083541431[82] = 0.0;
   out_1061940044083541431[83] = 0.0;
   out_1061940044083541431[84] = 0.0;
   out_1061940044083541431[85] = 0.0;
   out_1061940044083541431[86] = 0.0;
   out_1061940044083541431[87] = 0.0;
   out_1061940044083541431[88] = 0.0;
   out_1061940044083541431[89] = 0.0;
   out_1061940044083541431[90] = 0.0;
   out_1061940044083541431[91] = 0.0;
   out_1061940044083541431[92] = 0.0;
   out_1061940044083541431[93] = 0.0;
   out_1061940044083541431[94] = 0.0;
   out_1061940044083541431[95] = 1.0;
   out_1061940044083541431[96] = 0.0;
   out_1061940044083541431[97] = 0.0;
   out_1061940044083541431[98] = 0.0;
   out_1061940044083541431[99] = 0.0;
   out_1061940044083541431[100] = 0.0;
   out_1061940044083541431[101] = 0.0;
   out_1061940044083541431[102] = 0.0;
   out_1061940044083541431[103] = 0.0;
   out_1061940044083541431[104] = 0.0;
   out_1061940044083541431[105] = 0.0;
   out_1061940044083541431[106] = 0.0;
   out_1061940044083541431[107] = 0.0;
   out_1061940044083541431[108] = 0.0;
   out_1061940044083541431[109] = 0.0;
   out_1061940044083541431[110] = 0.0;
   out_1061940044083541431[111] = 0.0;
   out_1061940044083541431[112] = 0.0;
   out_1061940044083541431[113] = 0.0;
   out_1061940044083541431[114] = 1.0;
   out_1061940044083541431[115] = 0.0;
   out_1061940044083541431[116] = 0.0;
   out_1061940044083541431[117] = 0.0;
   out_1061940044083541431[118] = 0.0;
   out_1061940044083541431[119] = 0.0;
   out_1061940044083541431[120] = 0.0;
   out_1061940044083541431[121] = 0.0;
   out_1061940044083541431[122] = 0.0;
   out_1061940044083541431[123] = 0.0;
   out_1061940044083541431[124] = 0.0;
   out_1061940044083541431[125] = 0.0;
   out_1061940044083541431[126] = 0.0;
   out_1061940044083541431[127] = 0.0;
   out_1061940044083541431[128] = 0.0;
   out_1061940044083541431[129] = 0.0;
   out_1061940044083541431[130] = 0.0;
   out_1061940044083541431[131] = 0.0;
   out_1061940044083541431[132] = 0.0;
   out_1061940044083541431[133] = 1.0;
   out_1061940044083541431[134] = 0.0;
   out_1061940044083541431[135] = 0.0;
   out_1061940044083541431[136] = 0.0;
   out_1061940044083541431[137] = 0.0;
   out_1061940044083541431[138] = 0.0;
   out_1061940044083541431[139] = 0.0;
   out_1061940044083541431[140] = 0.0;
   out_1061940044083541431[141] = 0.0;
   out_1061940044083541431[142] = 0.0;
   out_1061940044083541431[143] = 0.0;
   out_1061940044083541431[144] = 0.0;
   out_1061940044083541431[145] = 0.0;
   out_1061940044083541431[146] = 0.0;
   out_1061940044083541431[147] = 0.0;
   out_1061940044083541431[148] = 0.0;
   out_1061940044083541431[149] = 0.0;
   out_1061940044083541431[150] = 0.0;
   out_1061940044083541431[151] = 0.0;
   out_1061940044083541431[152] = 1.0;
   out_1061940044083541431[153] = 0.0;
   out_1061940044083541431[154] = 0.0;
   out_1061940044083541431[155] = 0.0;
   out_1061940044083541431[156] = 0.0;
   out_1061940044083541431[157] = 0.0;
   out_1061940044083541431[158] = 0.0;
   out_1061940044083541431[159] = 0.0;
   out_1061940044083541431[160] = 0.0;
   out_1061940044083541431[161] = 0.0;
   out_1061940044083541431[162] = 0.0;
   out_1061940044083541431[163] = 0.0;
   out_1061940044083541431[164] = 0.0;
   out_1061940044083541431[165] = 0.0;
   out_1061940044083541431[166] = 0.0;
   out_1061940044083541431[167] = 0.0;
   out_1061940044083541431[168] = 0.0;
   out_1061940044083541431[169] = 0.0;
   out_1061940044083541431[170] = 0.0;
   out_1061940044083541431[171] = 1.0;
   out_1061940044083541431[172] = 0.0;
   out_1061940044083541431[173] = 0.0;
   out_1061940044083541431[174] = 0.0;
   out_1061940044083541431[175] = 0.0;
   out_1061940044083541431[176] = 0.0;
   out_1061940044083541431[177] = 0.0;
   out_1061940044083541431[178] = 0.0;
   out_1061940044083541431[179] = 0.0;
   out_1061940044083541431[180] = 0.0;
   out_1061940044083541431[181] = 0.0;
   out_1061940044083541431[182] = 0.0;
   out_1061940044083541431[183] = 0.0;
   out_1061940044083541431[184] = 0.0;
   out_1061940044083541431[185] = 0.0;
   out_1061940044083541431[186] = 0.0;
   out_1061940044083541431[187] = 0.0;
   out_1061940044083541431[188] = 0.0;
   out_1061940044083541431[189] = 0.0;
   out_1061940044083541431[190] = 1.0;
   out_1061940044083541431[191] = 0.0;
   out_1061940044083541431[192] = 0.0;
   out_1061940044083541431[193] = 0.0;
   out_1061940044083541431[194] = 0.0;
   out_1061940044083541431[195] = 0.0;
   out_1061940044083541431[196] = 0.0;
   out_1061940044083541431[197] = 0.0;
   out_1061940044083541431[198] = 0.0;
   out_1061940044083541431[199] = 0.0;
   out_1061940044083541431[200] = 0.0;
   out_1061940044083541431[201] = 0.0;
   out_1061940044083541431[202] = 0.0;
   out_1061940044083541431[203] = 0.0;
   out_1061940044083541431[204] = 0.0;
   out_1061940044083541431[205] = 0.0;
   out_1061940044083541431[206] = 0.0;
   out_1061940044083541431[207] = 0.0;
   out_1061940044083541431[208] = 0.0;
   out_1061940044083541431[209] = 1.0;
   out_1061940044083541431[210] = 0.0;
   out_1061940044083541431[211] = 0.0;
   out_1061940044083541431[212] = 0.0;
   out_1061940044083541431[213] = 0.0;
   out_1061940044083541431[214] = 0.0;
   out_1061940044083541431[215] = 0.0;
   out_1061940044083541431[216] = 0.0;
   out_1061940044083541431[217] = 0.0;
   out_1061940044083541431[218] = 0.0;
   out_1061940044083541431[219] = 0.0;
   out_1061940044083541431[220] = 0.0;
   out_1061940044083541431[221] = 0.0;
   out_1061940044083541431[222] = 0.0;
   out_1061940044083541431[223] = 0.0;
   out_1061940044083541431[224] = 0.0;
   out_1061940044083541431[225] = 0.0;
   out_1061940044083541431[226] = 0.0;
   out_1061940044083541431[227] = 0.0;
   out_1061940044083541431[228] = 1.0;
   out_1061940044083541431[229] = 0.0;
   out_1061940044083541431[230] = 0.0;
   out_1061940044083541431[231] = 0.0;
   out_1061940044083541431[232] = 0.0;
   out_1061940044083541431[233] = 0.0;
   out_1061940044083541431[234] = 0.0;
   out_1061940044083541431[235] = 0.0;
   out_1061940044083541431[236] = 0.0;
   out_1061940044083541431[237] = 0.0;
   out_1061940044083541431[238] = 0.0;
   out_1061940044083541431[239] = 0.0;
   out_1061940044083541431[240] = 0.0;
   out_1061940044083541431[241] = 0.0;
   out_1061940044083541431[242] = 0.0;
   out_1061940044083541431[243] = 0.0;
   out_1061940044083541431[244] = 0.0;
   out_1061940044083541431[245] = 0.0;
   out_1061940044083541431[246] = 0.0;
   out_1061940044083541431[247] = 1.0;
   out_1061940044083541431[248] = 0.0;
   out_1061940044083541431[249] = 0.0;
   out_1061940044083541431[250] = 0.0;
   out_1061940044083541431[251] = 0.0;
   out_1061940044083541431[252] = 0.0;
   out_1061940044083541431[253] = 0.0;
   out_1061940044083541431[254] = 0.0;
   out_1061940044083541431[255] = 0.0;
   out_1061940044083541431[256] = 0.0;
   out_1061940044083541431[257] = 0.0;
   out_1061940044083541431[258] = 0.0;
   out_1061940044083541431[259] = 0.0;
   out_1061940044083541431[260] = 0.0;
   out_1061940044083541431[261] = 0.0;
   out_1061940044083541431[262] = 0.0;
   out_1061940044083541431[263] = 0.0;
   out_1061940044083541431[264] = 0.0;
   out_1061940044083541431[265] = 0.0;
   out_1061940044083541431[266] = 1.0;
   out_1061940044083541431[267] = 0.0;
   out_1061940044083541431[268] = 0.0;
   out_1061940044083541431[269] = 0.0;
   out_1061940044083541431[270] = 0.0;
   out_1061940044083541431[271] = 0.0;
   out_1061940044083541431[272] = 0.0;
   out_1061940044083541431[273] = 0.0;
   out_1061940044083541431[274] = 0.0;
   out_1061940044083541431[275] = 0.0;
   out_1061940044083541431[276] = 0.0;
   out_1061940044083541431[277] = 0.0;
   out_1061940044083541431[278] = 0.0;
   out_1061940044083541431[279] = 0.0;
   out_1061940044083541431[280] = 0.0;
   out_1061940044083541431[281] = 0.0;
   out_1061940044083541431[282] = 0.0;
   out_1061940044083541431[283] = 0.0;
   out_1061940044083541431[284] = 0.0;
   out_1061940044083541431[285] = 1.0;
   out_1061940044083541431[286] = 0.0;
   out_1061940044083541431[287] = 0.0;
   out_1061940044083541431[288] = 0.0;
   out_1061940044083541431[289] = 0.0;
   out_1061940044083541431[290] = 0.0;
   out_1061940044083541431[291] = 0.0;
   out_1061940044083541431[292] = 0.0;
   out_1061940044083541431[293] = 0.0;
   out_1061940044083541431[294] = 0.0;
   out_1061940044083541431[295] = 0.0;
   out_1061940044083541431[296] = 0.0;
   out_1061940044083541431[297] = 0.0;
   out_1061940044083541431[298] = 0.0;
   out_1061940044083541431[299] = 0.0;
   out_1061940044083541431[300] = 0.0;
   out_1061940044083541431[301] = 0.0;
   out_1061940044083541431[302] = 0.0;
   out_1061940044083541431[303] = 0.0;
   out_1061940044083541431[304] = 1.0;
   out_1061940044083541431[305] = 0.0;
   out_1061940044083541431[306] = 0.0;
   out_1061940044083541431[307] = 0.0;
   out_1061940044083541431[308] = 0.0;
   out_1061940044083541431[309] = 0.0;
   out_1061940044083541431[310] = 0.0;
   out_1061940044083541431[311] = 0.0;
   out_1061940044083541431[312] = 0.0;
   out_1061940044083541431[313] = 0.0;
   out_1061940044083541431[314] = 0.0;
   out_1061940044083541431[315] = 0.0;
   out_1061940044083541431[316] = 0.0;
   out_1061940044083541431[317] = 0.0;
   out_1061940044083541431[318] = 0.0;
   out_1061940044083541431[319] = 0.0;
   out_1061940044083541431[320] = 0.0;
   out_1061940044083541431[321] = 0.0;
   out_1061940044083541431[322] = 0.0;
   out_1061940044083541431[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_3240563005197080216) {
   out_3240563005197080216[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_3240563005197080216[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_3240563005197080216[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_3240563005197080216[3] = dt*state[12] + state[3];
   out_3240563005197080216[4] = dt*state[13] + state[4];
   out_3240563005197080216[5] = dt*state[14] + state[5];
   out_3240563005197080216[6] = state[6];
   out_3240563005197080216[7] = state[7];
   out_3240563005197080216[8] = state[8];
   out_3240563005197080216[9] = state[9];
   out_3240563005197080216[10] = state[10];
   out_3240563005197080216[11] = state[11];
   out_3240563005197080216[12] = state[12];
   out_3240563005197080216[13] = state[13];
   out_3240563005197080216[14] = state[14];
   out_3240563005197080216[15] = state[15];
   out_3240563005197080216[16] = state[16];
   out_3240563005197080216[17] = state[17];
}
void F_fun(double *state, double dt, double *out_5982976038096974601) {
   out_5982976038096974601[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5982976038096974601[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5982976038096974601[2] = 0;
   out_5982976038096974601[3] = 0;
   out_5982976038096974601[4] = 0;
   out_5982976038096974601[5] = 0;
   out_5982976038096974601[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5982976038096974601[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5982976038096974601[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5982976038096974601[9] = 0;
   out_5982976038096974601[10] = 0;
   out_5982976038096974601[11] = 0;
   out_5982976038096974601[12] = 0;
   out_5982976038096974601[13] = 0;
   out_5982976038096974601[14] = 0;
   out_5982976038096974601[15] = 0;
   out_5982976038096974601[16] = 0;
   out_5982976038096974601[17] = 0;
   out_5982976038096974601[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5982976038096974601[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5982976038096974601[20] = 0;
   out_5982976038096974601[21] = 0;
   out_5982976038096974601[22] = 0;
   out_5982976038096974601[23] = 0;
   out_5982976038096974601[24] = 0;
   out_5982976038096974601[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5982976038096974601[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5982976038096974601[27] = 0;
   out_5982976038096974601[28] = 0;
   out_5982976038096974601[29] = 0;
   out_5982976038096974601[30] = 0;
   out_5982976038096974601[31] = 0;
   out_5982976038096974601[32] = 0;
   out_5982976038096974601[33] = 0;
   out_5982976038096974601[34] = 0;
   out_5982976038096974601[35] = 0;
   out_5982976038096974601[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5982976038096974601[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5982976038096974601[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5982976038096974601[39] = 0;
   out_5982976038096974601[40] = 0;
   out_5982976038096974601[41] = 0;
   out_5982976038096974601[42] = 0;
   out_5982976038096974601[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5982976038096974601[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5982976038096974601[45] = 0;
   out_5982976038096974601[46] = 0;
   out_5982976038096974601[47] = 0;
   out_5982976038096974601[48] = 0;
   out_5982976038096974601[49] = 0;
   out_5982976038096974601[50] = 0;
   out_5982976038096974601[51] = 0;
   out_5982976038096974601[52] = 0;
   out_5982976038096974601[53] = 0;
   out_5982976038096974601[54] = 0;
   out_5982976038096974601[55] = 0;
   out_5982976038096974601[56] = 0;
   out_5982976038096974601[57] = 1;
   out_5982976038096974601[58] = 0;
   out_5982976038096974601[59] = 0;
   out_5982976038096974601[60] = 0;
   out_5982976038096974601[61] = 0;
   out_5982976038096974601[62] = 0;
   out_5982976038096974601[63] = 0;
   out_5982976038096974601[64] = 0;
   out_5982976038096974601[65] = 0;
   out_5982976038096974601[66] = dt;
   out_5982976038096974601[67] = 0;
   out_5982976038096974601[68] = 0;
   out_5982976038096974601[69] = 0;
   out_5982976038096974601[70] = 0;
   out_5982976038096974601[71] = 0;
   out_5982976038096974601[72] = 0;
   out_5982976038096974601[73] = 0;
   out_5982976038096974601[74] = 0;
   out_5982976038096974601[75] = 0;
   out_5982976038096974601[76] = 1;
   out_5982976038096974601[77] = 0;
   out_5982976038096974601[78] = 0;
   out_5982976038096974601[79] = 0;
   out_5982976038096974601[80] = 0;
   out_5982976038096974601[81] = 0;
   out_5982976038096974601[82] = 0;
   out_5982976038096974601[83] = 0;
   out_5982976038096974601[84] = 0;
   out_5982976038096974601[85] = dt;
   out_5982976038096974601[86] = 0;
   out_5982976038096974601[87] = 0;
   out_5982976038096974601[88] = 0;
   out_5982976038096974601[89] = 0;
   out_5982976038096974601[90] = 0;
   out_5982976038096974601[91] = 0;
   out_5982976038096974601[92] = 0;
   out_5982976038096974601[93] = 0;
   out_5982976038096974601[94] = 0;
   out_5982976038096974601[95] = 1;
   out_5982976038096974601[96] = 0;
   out_5982976038096974601[97] = 0;
   out_5982976038096974601[98] = 0;
   out_5982976038096974601[99] = 0;
   out_5982976038096974601[100] = 0;
   out_5982976038096974601[101] = 0;
   out_5982976038096974601[102] = 0;
   out_5982976038096974601[103] = 0;
   out_5982976038096974601[104] = dt;
   out_5982976038096974601[105] = 0;
   out_5982976038096974601[106] = 0;
   out_5982976038096974601[107] = 0;
   out_5982976038096974601[108] = 0;
   out_5982976038096974601[109] = 0;
   out_5982976038096974601[110] = 0;
   out_5982976038096974601[111] = 0;
   out_5982976038096974601[112] = 0;
   out_5982976038096974601[113] = 0;
   out_5982976038096974601[114] = 1;
   out_5982976038096974601[115] = 0;
   out_5982976038096974601[116] = 0;
   out_5982976038096974601[117] = 0;
   out_5982976038096974601[118] = 0;
   out_5982976038096974601[119] = 0;
   out_5982976038096974601[120] = 0;
   out_5982976038096974601[121] = 0;
   out_5982976038096974601[122] = 0;
   out_5982976038096974601[123] = 0;
   out_5982976038096974601[124] = 0;
   out_5982976038096974601[125] = 0;
   out_5982976038096974601[126] = 0;
   out_5982976038096974601[127] = 0;
   out_5982976038096974601[128] = 0;
   out_5982976038096974601[129] = 0;
   out_5982976038096974601[130] = 0;
   out_5982976038096974601[131] = 0;
   out_5982976038096974601[132] = 0;
   out_5982976038096974601[133] = 1;
   out_5982976038096974601[134] = 0;
   out_5982976038096974601[135] = 0;
   out_5982976038096974601[136] = 0;
   out_5982976038096974601[137] = 0;
   out_5982976038096974601[138] = 0;
   out_5982976038096974601[139] = 0;
   out_5982976038096974601[140] = 0;
   out_5982976038096974601[141] = 0;
   out_5982976038096974601[142] = 0;
   out_5982976038096974601[143] = 0;
   out_5982976038096974601[144] = 0;
   out_5982976038096974601[145] = 0;
   out_5982976038096974601[146] = 0;
   out_5982976038096974601[147] = 0;
   out_5982976038096974601[148] = 0;
   out_5982976038096974601[149] = 0;
   out_5982976038096974601[150] = 0;
   out_5982976038096974601[151] = 0;
   out_5982976038096974601[152] = 1;
   out_5982976038096974601[153] = 0;
   out_5982976038096974601[154] = 0;
   out_5982976038096974601[155] = 0;
   out_5982976038096974601[156] = 0;
   out_5982976038096974601[157] = 0;
   out_5982976038096974601[158] = 0;
   out_5982976038096974601[159] = 0;
   out_5982976038096974601[160] = 0;
   out_5982976038096974601[161] = 0;
   out_5982976038096974601[162] = 0;
   out_5982976038096974601[163] = 0;
   out_5982976038096974601[164] = 0;
   out_5982976038096974601[165] = 0;
   out_5982976038096974601[166] = 0;
   out_5982976038096974601[167] = 0;
   out_5982976038096974601[168] = 0;
   out_5982976038096974601[169] = 0;
   out_5982976038096974601[170] = 0;
   out_5982976038096974601[171] = 1;
   out_5982976038096974601[172] = 0;
   out_5982976038096974601[173] = 0;
   out_5982976038096974601[174] = 0;
   out_5982976038096974601[175] = 0;
   out_5982976038096974601[176] = 0;
   out_5982976038096974601[177] = 0;
   out_5982976038096974601[178] = 0;
   out_5982976038096974601[179] = 0;
   out_5982976038096974601[180] = 0;
   out_5982976038096974601[181] = 0;
   out_5982976038096974601[182] = 0;
   out_5982976038096974601[183] = 0;
   out_5982976038096974601[184] = 0;
   out_5982976038096974601[185] = 0;
   out_5982976038096974601[186] = 0;
   out_5982976038096974601[187] = 0;
   out_5982976038096974601[188] = 0;
   out_5982976038096974601[189] = 0;
   out_5982976038096974601[190] = 1;
   out_5982976038096974601[191] = 0;
   out_5982976038096974601[192] = 0;
   out_5982976038096974601[193] = 0;
   out_5982976038096974601[194] = 0;
   out_5982976038096974601[195] = 0;
   out_5982976038096974601[196] = 0;
   out_5982976038096974601[197] = 0;
   out_5982976038096974601[198] = 0;
   out_5982976038096974601[199] = 0;
   out_5982976038096974601[200] = 0;
   out_5982976038096974601[201] = 0;
   out_5982976038096974601[202] = 0;
   out_5982976038096974601[203] = 0;
   out_5982976038096974601[204] = 0;
   out_5982976038096974601[205] = 0;
   out_5982976038096974601[206] = 0;
   out_5982976038096974601[207] = 0;
   out_5982976038096974601[208] = 0;
   out_5982976038096974601[209] = 1;
   out_5982976038096974601[210] = 0;
   out_5982976038096974601[211] = 0;
   out_5982976038096974601[212] = 0;
   out_5982976038096974601[213] = 0;
   out_5982976038096974601[214] = 0;
   out_5982976038096974601[215] = 0;
   out_5982976038096974601[216] = 0;
   out_5982976038096974601[217] = 0;
   out_5982976038096974601[218] = 0;
   out_5982976038096974601[219] = 0;
   out_5982976038096974601[220] = 0;
   out_5982976038096974601[221] = 0;
   out_5982976038096974601[222] = 0;
   out_5982976038096974601[223] = 0;
   out_5982976038096974601[224] = 0;
   out_5982976038096974601[225] = 0;
   out_5982976038096974601[226] = 0;
   out_5982976038096974601[227] = 0;
   out_5982976038096974601[228] = 1;
   out_5982976038096974601[229] = 0;
   out_5982976038096974601[230] = 0;
   out_5982976038096974601[231] = 0;
   out_5982976038096974601[232] = 0;
   out_5982976038096974601[233] = 0;
   out_5982976038096974601[234] = 0;
   out_5982976038096974601[235] = 0;
   out_5982976038096974601[236] = 0;
   out_5982976038096974601[237] = 0;
   out_5982976038096974601[238] = 0;
   out_5982976038096974601[239] = 0;
   out_5982976038096974601[240] = 0;
   out_5982976038096974601[241] = 0;
   out_5982976038096974601[242] = 0;
   out_5982976038096974601[243] = 0;
   out_5982976038096974601[244] = 0;
   out_5982976038096974601[245] = 0;
   out_5982976038096974601[246] = 0;
   out_5982976038096974601[247] = 1;
   out_5982976038096974601[248] = 0;
   out_5982976038096974601[249] = 0;
   out_5982976038096974601[250] = 0;
   out_5982976038096974601[251] = 0;
   out_5982976038096974601[252] = 0;
   out_5982976038096974601[253] = 0;
   out_5982976038096974601[254] = 0;
   out_5982976038096974601[255] = 0;
   out_5982976038096974601[256] = 0;
   out_5982976038096974601[257] = 0;
   out_5982976038096974601[258] = 0;
   out_5982976038096974601[259] = 0;
   out_5982976038096974601[260] = 0;
   out_5982976038096974601[261] = 0;
   out_5982976038096974601[262] = 0;
   out_5982976038096974601[263] = 0;
   out_5982976038096974601[264] = 0;
   out_5982976038096974601[265] = 0;
   out_5982976038096974601[266] = 1;
   out_5982976038096974601[267] = 0;
   out_5982976038096974601[268] = 0;
   out_5982976038096974601[269] = 0;
   out_5982976038096974601[270] = 0;
   out_5982976038096974601[271] = 0;
   out_5982976038096974601[272] = 0;
   out_5982976038096974601[273] = 0;
   out_5982976038096974601[274] = 0;
   out_5982976038096974601[275] = 0;
   out_5982976038096974601[276] = 0;
   out_5982976038096974601[277] = 0;
   out_5982976038096974601[278] = 0;
   out_5982976038096974601[279] = 0;
   out_5982976038096974601[280] = 0;
   out_5982976038096974601[281] = 0;
   out_5982976038096974601[282] = 0;
   out_5982976038096974601[283] = 0;
   out_5982976038096974601[284] = 0;
   out_5982976038096974601[285] = 1;
   out_5982976038096974601[286] = 0;
   out_5982976038096974601[287] = 0;
   out_5982976038096974601[288] = 0;
   out_5982976038096974601[289] = 0;
   out_5982976038096974601[290] = 0;
   out_5982976038096974601[291] = 0;
   out_5982976038096974601[292] = 0;
   out_5982976038096974601[293] = 0;
   out_5982976038096974601[294] = 0;
   out_5982976038096974601[295] = 0;
   out_5982976038096974601[296] = 0;
   out_5982976038096974601[297] = 0;
   out_5982976038096974601[298] = 0;
   out_5982976038096974601[299] = 0;
   out_5982976038096974601[300] = 0;
   out_5982976038096974601[301] = 0;
   out_5982976038096974601[302] = 0;
   out_5982976038096974601[303] = 0;
   out_5982976038096974601[304] = 1;
   out_5982976038096974601[305] = 0;
   out_5982976038096974601[306] = 0;
   out_5982976038096974601[307] = 0;
   out_5982976038096974601[308] = 0;
   out_5982976038096974601[309] = 0;
   out_5982976038096974601[310] = 0;
   out_5982976038096974601[311] = 0;
   out_5982976038096974601[312] = 0;
   out_5982976038096974601[313] = 0;
   out_5982976038096974601[314] = 0;
   out_5982976038096974601[315] = 0;
   out_5982976038096974601[316] = 0;
   out_5982976038096974601[317] = 0;
   out_5982976038096974601[318] = 0;
   out_5982976038096974601[319] = 0;
   out_5982976038096974601[320] = 0;
   out_5982976038096974601[321] = 0;
   out_5982976038096974601[322] = 0;
   out_5982976038096974601[323] = 1;
}
void h_4(double *state, double *unused, double *out_3015297743882558799) {
   out_3015297743882558799[0] = state[6] + state[9];
   out_3015297743882558799[1] = state[7] + state[10];
   out_3015297743882558799[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8440442363568188843) {
   out_8440442363568188843[0] = 0;
   out_8440442363568188843[1] = 0;
   out_8440442363568188843[2] = 0;
   out_8440442363568188843[3] = 0;
   out_8440442363568188843[4] = 0;
   out_8440442363568188843[5] = 0;
   out_8440442363568188843[6] = 1;
   out_8440442363568188843[7] = 0;
   out_8440442363568188843[8] = 0;
   out_8440442363568188843[9] = 1;
   out_8440442363568188843[10] = 0;
   out_8440442363568188843[11] = 0;
   out_8440442363568188843[12] = 0;
   out_8440442363568188843[13] = 0;
   out_8440442363568188843[14] = 0;
   out_8440442363568188843[15] = 0;
   out_8440442363568188843[16] = 0;
   out_8440442363568188843[17] = 0;
   out_8440442363568188843[18] = 0;
   out_8440442363568188843[19] = 0;
   out_8440442363568188843[20] = 0;
   out_8440442363568188843[21] = 0;
   out_8440442363568188843[22] = 0;
   out_8440442363568188843[23] = 0;
   out_8440442363568188843[24] = 0;
   out_8440442363568188843[25] = 1;
   out_8440442363568188843[26] = 0;
   out_8440442363568188843[27] = 0;
   out_8440442363568188843[28] = 1;
   out_8440442363568188843[29] = 0;
   out_8440442363568188843[30] = 0;
   out_8440442363568188843[31] = 0;
   out_8440442363568188843[32] = 0;
   out_8440442363568188843[33] = 0;
   out_8440442363568188843[34] = 0;
   out_8440442363568188843[35] = 0;
   out_8440442363568188843[36] = 0;
   out_8440442363568188843[37] = 0;
   out_8440442363568188843[38] = 0;
   out_8440442363568188843[39] = 0;
   out_8440442363568188843[40] = 0;
   out_8440442363568188843[41] = 0;
   out_8440442363568188843[42] = 0;
   out_8440442363568188843[43] = 0;
   out_8440442363568188843[44] = 1;
   out_8440442363568188843[45] = 0;
   out_8440442363568188843[46] = 0;
   out_8440442363568188843[47] = 1;
   out_8440442363568188843[48] = 0;
   out_8440442363568188843[49] = 0;
   out_8440442363568188843[50] = 0;
   out_8440442363568188843[51] = 0;
   out_8440442363568188843[52] = 0;
   out_8440442363568188843[53] = 0;
}
void h_10(double *state, double *unused, double *out_4712013892887729118) {
   out_4712013892887729118[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_4712013892887729118[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_4712013892887729118[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_747450665488565157) {
   out_747450665488565157[0] = 0;
   out_747450665488565157[1] = 9.8100000000000005*cos(state[1]);
   out_747450665488565157[2] = 0;
   out_747450665488565157[3] = 0;
   out_747450665488565157[4] = -state[8];
   out_747450665488565157[5] = state[7];
   out_747450665488565157[6] = 0;
   out_747450665488565157[7] = state[5];
   out_747450665488565157[8] = -state[4];
   out_747450665488565157[9] = 0;
   out_747450665488565157[10] = 0;
   out_747450665488565157[11] = 0;
   out_747450665488565157[12] = 1;
   out_747450665488565157[13] = 0;
   out_747450665488565157[14] = 0;
   out_747450665488565157[15] = 1;
   out_747450665488565157[16] = 0;
   out_747450665488565157[17] = 0;
   out_747450665488565157[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_747450665488565157[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_747450665488565157[20] = 0;
   out_747450665488565157[21] = state[8];
   out_747450665488565157[22] = 0;
   out_747450665488565157[23] = -state[6];
   out_747450665488565157[24] = -state[5];
   out_747450665488565157[25] = 0;
   out_747450665488565157[26] = state[3];
   out_747450665488565157[27] = 0;
   out_747450665488565157[28] = 0;
   out_747450665488565157[29] = 0;
   out_747450665488565157[30] = 0;
   out_747450665488565157[31] = 1;
   out_747450665488565157[32] = 0;
   out_747450665488565157[33] = 0;
   out_747450665488565157[34] = 1;
   out_747450665488565157[35] = 0;
   out_747450665488565157[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_747450665488565157[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_747450665488565157[38] = 0;
   out_747450665488565157[39] = -state[7];
   out_747450665488565157[40] = state[6];
   out_747450665488565157[41] = 0;
   out_747450665488565157[42] = state[4];
   out_747450665488565157[43] = -state[3];
   out_747450665488565157[44] = 0;
   out_747450665488565157[45] = 0;
   out_747450665488565157[46] = 0;
   out_747450665488565157[47] = 0;
   out_747450665488565157[48] = 0;
   out_747450665488565157[49] = 0;
   out_747450665488565157[50] = 1;
   out_747450665488565157[51] = 0;
   out_747450665488565157[52] = 0;
   out_747450665488565157[53] = 1;
}
void h_13(double *state, double *unused, double *out_413147883148967273) {
   out_413147883148967273[0] = state[3];
   out_413147883148967273[1] = state[4];
   out_413147883148967273[2] = state[5];
}
void H_13(double *state, double *unused, double *out_6794027884809029972) {
   out_6794027884809029972[0] = 0;
   out_6794027884809029972[1] = 0;
   out_6794027884809029972[2] = 0;
   out_6794027884809029972[3] = 1;
   out_6794027884809029972[4] = 0;
   out_6794027884809029972[5] = 0;
   out_6794027884809029972[6] = 0;
   out_6794027884809029972[7] = 0;
   out_6794027884809029972[8] = 0;
   out_6794027884809029972[9] = 0;
   out_6794027884809029972[10] = 0;
   out_6794027884809029972[11] = 0;
   out_6794027884809029972[12] = 0;
   out_6794027884809029972[13] = 0;
   out_6794027884809029972[14] = 0;
   out_6794027884809029972[15] = 0;
   out_6794027884809029972[16] = 0;
   out_6794027884809029972[17] = 0;
   out_6794027884809029972[18] = 0;
   out_6794027884809029972[19] = 0;
   out_6794027884809029972[20] = 0;
   out_6794027884809029972[21] = 0;
   out_6794027884809029972[22] = 1;
   out_6794027884809029972[23] = 0;
   out_6794027884809029972[24] = 0;
   out_6794027884809029972[25] = 0;
   out_6794027884809029972[26] = 0;
   out_6794027884809029972[27] = 0;
   out_6794027884809029972[28] = 0;
   out_6794027884809029972[29] = 0;
   out_6794027884809029972[30] = 0;
   out_6794027884809029972[31] = 0;
   out_6794027884809029972[32] = 0;
   out_6794027884809029972[33] = 0;
   out_6794027884809029972[34] = 0;
   out_6794027884809029972[35] = 0;
   out_6794027884809029972[36] = 0;
   out_6794027884809029972[37] = 0;
   out_6794027884809029972[38] = 0;
   out_6794027884809029972[39] = 0;
   out_6794027884809029972[40] = 0;
   out_6794027884809029972[41] = 1;
   out_6794027884809029972[42] = 0;
   out_6794027884809029972[43] = 0;
   out_6794027884809029972[44] = 0;
   out_6794027884809029972[45] = 0;
   out_6794027884809029972[46] = 0;
   out_6794027884809029972[47] = 0;
   out_6794027884809029972[48] = 0;
   out_6794027884809029972[49] = 0;
   out_6794027884809029972[50] = 0;
   out_6794027884809029972[51] = 0;
   out_6794027884809029972[52] = 0;
   out_6794027884809029972[53] = 0;
}
void h_14(double *state, double *unused, double *out_2902963862180291092) {
   out_2902963862180291092[0] = state[6];
   out_2902963862180291092[1] = state[7];
   out_2902963862180291092[2] = state[8];
}
void H_14(double *state, double *unused, double *out_5357653931272816547) {
   out_5357653931272816547[0] = 0;
   out_5357653931272816547[1] = 0;
   out_5357653931272816547[2] = 0;
   out_5357653931272816547[3] = 0;
   out_5357653931272816547[4] = 0;
   out_5357653931272816547[5] = 0;
   out_5357653931272816547[6] = 1;
   out_5357653931272816547[7] = 0;
   out_5357653931272816547[8] = 0;
   out_5357653931272816547[9] = 0;
   out_5357653931272816547[10] = 0;
   out_5357653931272816547[11] = 0;
   out_5357653931272816547[12] = 0;
   out_5357653931272816547[13] = 0;
   out_5357653931272816547[14] = 0;
   out_5357653931272816547[15] = 0;
   out_5357653931272816547[16] = 0;
   out_5357653931272816547[17] = 0;
   out_5357653931272816547[18] = 0;
   out_5357653931272816547[19] = 0;
   out_5357653931272816547[20] = 0;
   out_5357653931272816547[21] = 0;
   out_5357653931272816547[22] = 0;
   out_5357653931272816547[23] = 0;
   out_5357653931272816547[24] = 0;
   out_5357653931272816547[25] = 1;
   out_5357653931272816547[26] = 0;
   out_5357653931272816547[27] = 0;
   out_5357653931272816547[28] = 0;
   out_5357653931272816547[29] = 0;
   out_5357653931272816547[30] = 0;
   out_5357653931272816547[31] = 0;
   out_5357653931272816547[32] = 0;
   out_5357653931272816547[33] = 0;
   out_5357653931272816547[34] = 0;
   out_5357653931272816547[35] = 0;
   out_5357653931272816547[36] = 0;
   out_5357653931272816547[37] = 0;
   out_5357653931272816547[38] = 0;
   out_5357653931272816547[39] = 0;
   out_5357653931272816547[40] = 0;
   out_5357653931272816547[41] = 0;
   out_5357653931272816547[42] = 0;
   out_5357653931272816547[43] = 0;
   out_5357653931272816547[44] = 1;
   out_5357653931272816547[45] = 0;
   out_5357653931272816547[46] = 0;
   out_5357653931272816547[47] = 0;
   out_5357653931272816547[48] = 0;
   out_5357653931272816547[49] = 0;
   out_5357653931272816547[50] = 0;
   out_5357653931272816547[51] = 0;
   out_5357653931272816547[52] = 0;
   out_5357653931272816547[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_1002597543094682529) {
  err_fun(nom_x, delta_x, out_1002597543094682529);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6790221310632921126) {
  inv_err_fun(nom_x, true_x, out_6790221310632921126);
}
void pose_H_mod_fun(double *state, double *out_1061940044083541431) {
  H_mod_fun(state, out_1061940044083541431);
}
void pose_f_fun(double *state, double dt, double *out_3240563005197080216) {
  f_fun(state,  dt, out_3240563005197080216);
}
void pose_F_fun(double *state, double dt, double *out_5982976038096974601) {
  F_fun(state,  dt, out_5982976038096974601);
}
void pose_h_4(double *state, double *unused, double *out_3015297743882558799) {
  h_4(state, unused, out_3015297743882558799);
}
void pose_H_4(double *state, double *unused, double *out_8440442363568188843) {
  H_4(state, unused, out_8440442363568188843);
}
void pose_h_10(double *state, double *unused, double *out_4712013892887729118) {
  h_10(state, unused, out_4712013892887729118);
}
void pose_H_10(double *state, double *unused, double *out_747450665488565157) {
  H_10(state, unused, out_747450665488565157);
}
void pose_h_13(double *state, double *unused, double *out_413147883148967273) {
  h_13(state, unused, out_413147883148967273);
}
void pose_H_13(double *state, double *unused, double *out_6794027884809029972) {
  H_13(state, unused, out_6794027884809029972);
}
void pose_h_14(double *state, double *unused, double *out_2902963862180291092) {
  h_14(state, unused, out_2902963862180291092);
}
void pose_H_14(double *state, double *unused, double *out_5357653931272816547) {
  H_14(state, unused, out_5357653931272816547);
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
