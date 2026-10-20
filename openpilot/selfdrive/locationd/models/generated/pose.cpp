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
void err_fun(double *nom_x, double *delta_x, double *out_6044847391441660522) {
   out_6044847391441660522[0] = delta_x[0] + nom_x[0];
   out_6044847391441660522[1] = delta_x[1] + nom_x[1];
   out_6044847391441660522[2] = delta_x[2] + nom_x[2];
   out_6044847391441660522[3] = delta_x[3] + nom_x[3];
   out_6044847391441660522[4] = delta_x[4] + nom_x[4];
   out_6044847391441660522[5] = delta_x[5] + nom_x[5];
   out_6044847391441660522[6] = delta_x[6] + nom_x[6];
   out_6044847391441660522[7] = delta_x[7] + nom_x[7];
   out_6044847391441660522[8] = delta_x[8] + nom_x[8];
   out_6044847391441660522[9] = delta_x[9] + nom_x[9];
   out_6044847391441660522[10] = delta_x[10] + nom_x[10];
   out_6044847391441660522[11] = delta_x[11] + nom_x[11];
   out_6044847391441660522[12] = delta_x[12] + nom_x[12];
   out_6044847391441660522[13] = delta_x[13] + nom_x[13];
   out_6044847391441660522[14] = delta_x[14] + nom_x[14];
   out_6044847391441660522[15] = delta_x[15] + nom_x[15];
   out_6044847391441660522[16] = delta_x[16] + nom_x[16];
   out_6044847391441660522[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5641758511196693149) {
   out_5641758511196693149[0] = -nom_x[0] + true_x[0];
   out_5641758511196693149[1] = -nom_x[1] + true_x[1];
   out_5641758511196693149[2] = -nom_x[2] + true_x[2];
   out_5641758511196693149[3] = -nom_x[3] + true_x[3];
   out_5641758511196693149[4] = -nom_x[4] + true_x[4];
   out_5641758511196693149[5] = -nom_x[5] + true_x[5];
   out_5641758511196693149[6] = -nom_x[6] + true_x[6];
   out_5641758511196693149[7] = -nom_x[7] + true_x[7];
   out_5641758511196693149[8] = -nom_x[8] + true_x[8];
   out_5641758511196693149[9] = -nom_x[9] + true_x[9];
   out_5641758511196693149[10] = -nom_x[10] + true_x[10];
   out_5641758511196693149[11] = -nom_x[11] + true_x[11];
   out_5641758511196693149[12] = -nom_x[12] + true_x[12];
   out_5641758511196693149[13] = -nom_x[13] + true_x[13];
   out_5641758511196693149[14] = -nom_x[14] + true_x[14];
   out_5641758511196693149[15] = -nom_x[15] + true_x[15];
   out_5641758511196693149[16] = -nom_x[16] + true_x[16];
   out_5641758511196693149[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_3649931908543644442) {
   out_3649931908543644442[0] = 1.0;
   out_3649931908543644442[1] = 0.0;
   out_3649931908543644442[2] = 0.0;
   out_3649931908543644442[3] = 0.0;
   out_3649931908543644442[4] = 0.0;
   out_3649931908543644442[5] = 0.0;
   out_3649931908543644442[6] = 0.0;
   out_3649931908543644442[7] = 0.0;
   out_3649931908543644442[8] = 0.0;
   out_3649931908543644442[9] = 0.0;
   out_3649931908543644442[10] = 0.0;
   out_3649931908543644442[11] = 0.0;
   out_3649931908543644442[12] = 0.0;
   out_3649931908543644442[13] = 0.0;
   out_3649931908543644442[14] = 0.0;
   out_3649931908543644442[15] = 0.0;
   out_3649931908543644442[16] = 0.0;
   out_3649931908543644442[17] = 0.0;
   out_3649931908543644442[18] = 0.0;
   out_3649931908543644442[19] = 1.0;
   out_3649931908543644442[20] = 0.0;
   out_3649931908543644442[21] = 0.0;
   out_3649931908543644442[22] = 0.0;
   out_3649931908543644442[23] = 0.0;
   out_3649931908543644442[24] = 0.0;
   out_3649931908543644442[25] = 0.0;
   out_3649931908543644442[26] = 0.0;
   out_3649931908543644442[27] = 0.0;
   out_3649931908543644442[28] = 0.0;
   out_3649931908543644442[29] = 0.0;
   out_3649931908543644442[30] = 0.0;
   out_3649931908543644442[31] = 0.0;
   out_3649931908543644442[32] = 0.0;
   out_3649931908543644442[33] = 0.0;
   out_3649931908543644442[34] = 0.0;
   out_3649931908543644442[35] = 0.0;
   out_3649931908543644442[36] = 0.0;
   out_3649931908543644442[37] = 0.0;
   out_3649931908543644442[38] = 1.0;
   out_3649931908543644442[39] = 0.0;
   out_3649931908543644442[40] = 0.0;
   out_3649931908543644442[41] = 0.0;
   out_3649931908543644442[42] = 0.0;
   out_3649931908543644442[43] = 0.0;
   out_3649931908543644442[44] = 0.0;
   out_3649931908543644442[45] = 0.0;
   out_3649931908543644442[46] = 0.0;
   out_3649931908543644442[47] = 0.0;
   out_3649931908543644442[48] = 0.0;
   out_3649931908543644442[49] = 0.0;
   out_3649931908543644442[50] = 0.0;
   out_3649931908543644442[51] = 0.0;
   out_3649931908543644442[52] = 0.0;
   out_3649931908543644442[53] = 0.0;
   out_3649931908543644442[54] = 0.0;
   out_3649931908543644442[55] = 0.0;
   out_3649931908543644442[56] = 0.0;
   out_3649931908543644442[57] = 1.0;
   out_3649931908543644442[58] = 0.0;
   out_3649931908543644442[59] = 0.0;
   out_3649931908543644442[60] = 0.0;
   out_3649931908543644442[61] = 0.0;
   out_3649931908543644442[62] = 0.0;
   out_3649931908543644442[63] = 0.0;
   out_3649931908543644442[64] = 0.0;
   out_3649931908543644442[65] = 0.0;
   out_3649931908543644442[66] = 0.0;
   out_3649931908543644442[67] = 0.0;
   out_3649931908543644442[68] = 0.0;
   out_3649931908543644442[69] = 0.0;
   out_3649931908543644442[70] = 0.0;
   out_3649931908543644442[71] = 0.0;
   out_3649931908543644442[72] = 0.0;
   out_3649931908543644442[73] = 0.0;
   out_3649931908543644442[74] = 0.0;
   out_3649931908543644442[75] = 0.0;
   out_3649931908543644442[76] = 1.0;
   out_3649931908543644442[77] = 0.0;
   out_3649931908543644442[78] = 0.0;
   out_3649931908543644442[79] = 0.0;
   out_3649931908543644442[80] = 0.0;
   out_3649931908543644442[81] = 0.0;
   out_3649931908543644442[82] = 0.0;
   out_3649931908543644442[83] = 0.0;
   out_3649931908543644442[84] = 0.0;
   out_3649931908543644442[85] = 0.0;
   out_3649931908543644442[86] = 0.0;
   out_3649931908543644442[87] = 0.0;
   out_3649931908543644442[88] = 0.0;
   out_3649931908543644442[89] = 0.0;
   out_3649931908543644442[90] = 0.0;
   out_3649931908543644442[91] = 0.0;
   out_3649931908543644442[92] = 0.0;
   out_3649931908543644442[93] = 0.0;
   out_3649931908543644442[94] = 0.0;
   out_3649931908543644442[95] = 1.0;
   out_3649931908543644442[96] = 0.0;
   out_3649931908543644442[97] = 0.0;
   out_3649931908543644442[98] = 0.0;
   out_3649931908543644442[99] = 0.0;
   out_3649931908543644442[100] = 0.0;
   out_3649931908543644442[101] = 0.0;
   out_3649931908543644442[102] = 0.0;
   out_3649931908543644442[103] = 0.0;
   out_3649931908543644442[104] = 0.0;
   out_3649931908543644442[105] = 0.0;
   out_3649931908543644442[106] = 0.0;
   out_3649931908543644442[107] = 0.0;
   out_3649931908543644442[108] = 0.0;
   out_3649931908543644442[109] = 0.0;
   out_3649931908543644442[110] = 0.0;
   out_3649931908543644442[111] = 0.0;
   out_3649931908543644442[112] = 0.0;
   out_3649931908543644442[113] = 0.0;
   out_3649931908543644442[114] = 1.0;
   out_3649931908543644442[115] = 0.0;
   out_3649931908543644442[116] = 0.0;
   out_3649931908543644442[117] = 0.0;
   out_3649931908543644442[118] = 0.0;
   out_3649931908543644442[119] = 0.0;
   out_3649931908543644442[120] = 0.0;
   out_3649931908543644442[121] = 0.0;
   out_3649931908543644442[122] = 0.0;
   out_3649931908543644442[123] = 0.0;
   out_3649931908543644442[124] = 0.0;
   out_3649931908543644442[125] = 0.0;
   out_3649931908543644442[126] = 0.0;
   out_3649931908543644442[127] = 0.0;
   out_3649931908543644442[128] = 0.0;
   out_3649931908543644442[129] = 0.0;
   out_3649931908543644442[130] = 0.0;
   out_3649931908543644442[131] = 0.0;
   out_3649931908543644442[132] = 0.0;
   out_3649931908543644442[133] = 1.0;
   out_3649931908543644442[134] = 0.0;
   out_3649931908543644442[135] = 0.0;
   out_3649931908543644442[136] = 0.0;
   out_3649931908543644442[137] = 0.0;
   out_3649931908543644442[138] = 0.0;
   out_3649931908543644442[139] = 0.0;
   out_3649931908543644442[140] = 0.0;
   out_3649931908543644442[141] = 0.0;
   out_3649931908543644442[142] = 0.0;
   out_3649931908543644442[143] = 0.0;
   out_3649931908543644442[144] = 0.0;
   out_3649931908543644442[145] = 0.0;
   out_3649931908543644442[146] = 0.0;
   out_3649931908543644442[147] = 0.0;
   out_3649931908543644442[148] = 0.0;
   out_3649931908543644442[149] = 0.0;
   out_3649931908543644442[150] = 0.0;
   out_3649931908543644442[151] = 0.0;
   out_3649931908543644442[152] = 1.0;
   out_3649931908543644442[153] = 0.0;
   out_3649931908543644442[154] = 0.0;
   out_3649931908543644442[155] = 0.0;
   out_3649931908543644442[156] = 0.0;
   out_3649931908543644442[157] = 0.0;
   out_3649931908543644442[158] = 0.0;
   out_3649931908543644442[159] = 0.0;
   out_3649931908543644442[160] = 0.0;
   out_3649931908543644442[161] = 0.0;
   out_3649931908543644442[162] = 0.0;
   out_3649931908543644442[163] = 0.0;
   out_3649931908543644442[164] = 0.0;
   out_3649931908543644442[165] = 0.0;
   out_3649931908543644442[166] = 0.0;
   out_3649931908543644442[167] = 0.0;
   out_3649931908543644442[168] = 0.0;
   out_3649931908543644442[169] = 0.0;
   out_3649931908543644442[170] = 0.0;
   out_3649931908543644442[171] = 1.0;
   out_3649931908543644442[172] = 0.0;
   out_3649931908543644442[173] = 0.0;
   out_3649931908543644442[174] = 0.0;
   out_3649931908543644442[175] = 0.0;
   out_3649931908543644442[176] = 0.0;
   out_3649931908543644442[177] = 0.0;
   out_3649931908543644442[178] = 0.0;
   out_3649931908543644442[179] = 0.0;
   out_3649931908543644442[180] = 0.0;
   out_3649931908543644442[181] = 0.0;
   out_3649931908543644442[182] = 0.0;
   out_3649931908543644442[183] = 0.0;
   out_3649931908543644442[184] = 0.0;
   out_3649931908543644442[185] = 0.0;
   out_3649931908543644442[186] = 0.0;
   out_3649931908543644442[187] = 0.0;
   out_3649931908543644442[188] = 0.0;
   out_3649931908543644442[189] = 0.0;
   out_3649931908543644442[190] = 1.0;
   out_3649931908543644442[191] = 0.0;
   out_3649931908543644442[192] = 0.0;
   out_3649931908543644442[193] = 0.0;
   out_3649931908543644442[194] = 0.0;
   out_3649931908543644442[195] = 0.0;
   out_3649931908543644442[196] = 0.0;
   out_3649931908543644442[197] = 0.0;
   out_3649931908543644442[198] = 0.0;
   out_3649931908543644442[199] = 0.0;
   out_3649931908543644442[200] = 0.0;
   out_3649931908543644442[201] = 0.0;
   out_3649931908543644442[202] = 0.0;
   out_3649931908543644442[203] = 0.0;
   out_3649931908543644442[204] = 0.0;
   out_3649931908543644442[205] = 0.0;
   out_3649931908543644442[206] = 0.0;
   out_3649931908543644442[207] = 0.0;
   out_3649931908543644442[208] = 0.0;
   out_3649931908543644442[209] = 1.0;
   out_3649931908543644442[210] = 0.0;
   out_3649931908543644442[211] = 0.0;
   out_3649931908543644442[212] = 0.0;
   out_3649931908543644442[213] = 0.0;
   out_3649931908543644442[214] = 0.0;
   out_3649931908543644442[215] = 0.0;
   out_3649931908543644442[216] = 0.0;
   out_3649931908543644442[217] = 0.0;
   out_3649931908543644442[218] = 0.0;
   out_3649931908543644442[219] = 0.0;
   out_3649931908543644442[220] = 0.0;
   out_3649931908543644442[221] = 0.0;
   out_3649931908543644442[222] = 0.0;
   out_3649931908543644442[223] = 0.0;
   out_3649931908543644442[224] = 0.0;
   out_3649931908543644442[225] = 0.0;
   out_3649931908543644442[226] = 0.0;
   out_3649931908543644442[227] = 0.0;
   out_3649931908543644442[228] = 1.0;
   out_3649931908543644442[229] = 0.0;
   out_3649931908543644442[230] = 0.0;
   out_3649931908543644442[231] = 0.0;
   out_3649931908543644442[232] = 0.0;
   out_3649931908543644442[233] = 0.0;
   out_3649931908543644442[234] = 0.0;
   out_3649931908543644442[235] = 0.0;
   out_3649931908543644442[236] = 0.0;
   out_3649931908543644442[237] = 0.0;
   out_3649931908543644442[238] = 0.0;
   out_3649931908543644442[239] = 0.0;
   out_3649931908543644442[240] = 0.0;
   out_3649931908543644442[241] = 0.0;
   out_3649931908543644442[242] = 0.0;
   out_3649931908543644442[243] = 0.0;
   out_3649931908543644442[244] = 0.0;
   out_3649931908543644442[245] = 0.0;
   out_3649931908543644442[246] = 0.0;
   out_3649931908543644442[247] = 1.0;
   out_3649931908543644442[248] = 0.0;
   out_3649931908543644442[249] = 0.0;
   out_3649931908543644442[250] = 0.0;
   out_3649931908543644442[251] = 0.0;
   out_3649931908543644442[252] = 0.0;
   out_3649931908543644442[253] = 0.0;
   out_3649931908543644442[254] = 0.0;
   out_3649931908543644442[255] = 0.0;
   out_3649931908543644442[256] = 0.0;
   out_3649931908543644442[257] = 0.0;
   out_3649931908543644442[258] = 0.0;
   out_3649931908543644442[259] = 0.0;
   out_3649931908543644442[260] = 0.0;
   out_3649931908543644442[261] = 0.0;
   out_3649931908543644442[262] = 0.0;
   out_3649931908543644442[263] = 0.0;
   out_3649931908543644442[264] = 0.0;
   out_3649931908543644442[265] = 0.0;
   out_3649931908543644442[266] = 1.0;
   out_3649931908543644442[267] = 0.0;
   out_3649931908543644442[268] = 0.0;
   out_3649931908543644442[269] = 0.0;
   out_3649931908543644442[270] = 0.0;
   out_3649931908543644442[271] = 0.0;
   out_3649931908543644442[272] = 0.0;
   out_3649931908543644442[273] = 0.0;
   out_3649931908543644442[274] = 0.0;
   out_3649931908543644442[275] = 0.0;
   out_3649931908543644442[276] = 0.0;
   out_3649931908543644442[277] = 0.0;
   out_3649931908543644442[278] = 0.0;
   out_3649931908543644442[279] = 0.0;
   out_3649931908543644442[280] = 0.0;
   out_3649931908543644442[281] = 0.0;
   out_3649931908543644442[282] = 0.0;
   out_3649931908543644442[283] = 0.0;
   out_3649931908543644442[284] = 0.0;
   out_3649931908543644442[285] = 1.0;
   out_3649931908543644442[286] = 0.0;
   out_3649931908543644442[287] = 0.0;
   out_3649931908543644442[288] = 0.0;
   out_3649931908543644442[289] = 0.0;
   out_3649931908543644442[290] = 0.0;
   out_3649931908543644442[291] = 0.0;
   out_3649931908543644442[292] = 0.0;
   out_3649931908543644442[293] = 0.0;
   out_3649931908543644442[294] = 0.0;
   out_3649931908543644442[295] = 0.0;
   out_3649931908543644442[296] = 0.0;
   out_3649931908543644442[297] = 0.0;
   out_3649931908543644442[298] = 0.0;
   out_3649931908543644442[299] = 0.0;
   out_3649931908543644442[300] = 0.0;
   out_3649931908543644442[301] = 0.0;
   out_3649931908543644442[302] = 0.0;
   out_3649931908543644442[303] = 0.0;
   out_3649931908543644442[304] = 1.0;
   out_3649931908543644442[305] = 0.0;
   out_3649931908543644442[306] = 0.0;
   out_3649931908543644442[307] = 0.0;
   out_3649931908543644442[308] = 0.0;
   out_3649931908543644442[309] = 0.0;
   out_3649931908543644442[310] = 0.0;
   out_3649931908543644442[311] = 0.0;
   out_3649931908543644442[312] = 0.0;
   out_3649931908543644442[313] = 0.0;
   out_3649931908543644442[314] = 0.0;
   out_3649931908543644442[315] = 0.0;
   out_3649931908543644442[316] = 0.0;
   out_3649931908543644442[317] = 0.0;
   out_3649931908543644442[318] = 0.0;
   out_3649931908543644442[319] = 0.0;
   out_3649931908543644442[320] = 0.0;
   out_3649931908543644442[321] = 0.0;
   out_3649931908543644442[322] = 0.0;
   out_3649931908543644442[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_1050158138610913571) {
   out_1050158138610913571[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_1050158138610913571[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_1050158138610913571[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_1050158138610913571[3] = dt*state[12] + state[3];
   out_1050158138610913571[4] = dt*state[13] + state[4];
   out_1050158138610913571[5] = dt*state[14] + state[5];
   out_1050158138610913571[6] = state[6];
   out_1050158138610913571[7] = state[7];
   out_1050158138610913571[8] = state[8];
   out_1050158138610913571[9] = state[9];
   out_1050158138610913571[10] = state[10];
   out_1050158138610913571[11] = state[11];
   out_1050158138610913571[12] = state[12];
   out_1050158138610913571[13] = state[13];
   out_1050158138610913571[14] = state[14];
   out_1050158138610913571[15] = state[15];
   out_1050158138610913571[16] = state[16];
   out_1050158138610913571[17] = state[17];
}
void F_fun(double *state, double dt, double *out_7004170523943837202) {
   out_7004170523943837202[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7004170523943837202[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7004170523943837202[2] = 0;
   out_7004170523943837202[3] = 0;
   out_7004170523943837202[4] = 0;
   out_7004170523943837202[5] = 0;
   out_7004170523943837202[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7004170523943837202[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7004170523943837202[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_7004170523943837202[9] = 0;
   out_7004170523943837202[10] = 0;
   out_7004170523943837202[11] = 0;
   out_7004170523943837202[12] = 0;
   out_7004170523943837202[13] = 0;
   out_7004170523943837202[14] = 0;
   out_7004170523943837202[15] = 0;
   out_7004170523943837202[16] = 0;
   out_7004170523943837202[17] = 0;
   out_7004170523943837202[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7004170523943837202[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7004170523943837202[20] = 0;
   out_7004170523943837202[21] = 0;
   out_7004170523943837202[22] = 0;
   out_7004170523943837202[23] = 0;
   out_7004170523943837202[24] = 0;
   out_7004170523943837202[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7004170523943837202[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_7004170523943837202[27] = 0;
   out_7004170523943837202[28] = 0;
   out_7004170523943837202[29] = 0;
   out_7004170523943837202[30] = 0;
   out_7004170523943837202[31] = 0;
   out_7004170523943837202[32] = 0;
   out_7004170523943837202[33] = 0;
   out_7004170523943837202[34] = 0;
   out_7004170523943837202[35] = 0;
   out_7004170523943837202[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7004170523943837202[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7004170523943837202[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7004170523943837202[39] = 0;
   out_7004170523943837202[40] = 0;
   out_7004170523943837202[41] = 0;
   out_7004170523943837202[42] = 0;
   out_7004170523943837202[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7004170523943837202[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_7004170523943837202[45] = 0;
   out_7004170523943837202[46] = 0;
   out_7004170523943837202[47] = 0;
   out_7004170523943837202[48] = 0;
   out_7004170523943837202[49] = 0;
   out_7004170523943837202[50] = 0;
   out_7004170523943837202[51] = 0;
   out_7004170523943837202[52] = 0;
   out_7004170523943837202[53] = 0;
   out_7004170523943837202[54] = 0;
   out_7004170523943837202[55] = 0;
   out_7004170523943837202[56] = 0;
   out_7004170523943837202[57] = 1;
   out_7004170523943837202[58] = 0;
   out_7004170523943837202[59] = 0;
   out_7004170523943837202[60] = 0;
   out_7004170523943837202[61] = 0;
   out_7004170523943837202[62] = 0;
   out_7004170523943837202[63] = 0;
   out_7004170523943837202[64] = 0;
   out_7004170523943837202[65] = 0;
   out_7004170523943837202[66] = dt;
   out_7004170523943837202[67] = 0;
   out_7004170523943837202[68] = 0;
   out_7004170523943837202[69] = 0;
   out_7004170523943837202[70] = 0;
   out_7004170523943837202[71] = 0;
   out_7004170523943837202[72] = 0;
   out_7004170523943837202[73] = 0;
   out_7004170523943837202[74] = 0;
   out_7004170523943837202[75] = 0;
   out_7004170523943837202[76] = 1;
   out_7004170523943837202[77] = 0;
   out_7004170523943837202[78] = 0;
   out_7004170523943837202[79] = 0;
   out_7004170523943837202[80] = 0;
   out_7004170523943837202[81] = 0;
   out_7004170523943837202[82] = 0;
   out_7004170523943837202[83] = 0;
   out_7004170523943837202[84] = 0;
   out_7004170523943837202[85] = dt;
   out_7004170523943837202[86] = 0;
   out_7004170523943837202[87] = 0;
   out_7004170523943837202[88] = 0;
   out_7004170523943837202[89] = 0;
   out_7004170523943837202[90] = 0;
   out_7004170523943837202[91] = 0;
   out_7004170523943837202[92] = 0;
   out_7004170523943837202[93] = 0;
   out_7004170523943837202[94] = 0;
   out_7004170523943837202[95] = 1;
   out_7004170523943837202[96] = 0;
   out_7004170523943837202[97] = 0;
   out_7004170523943837202[98] = 0;
   out_7004170523943837202[99] = 0;
   out_7004170523943837202[100] = 0;
   out_7004170523943837202[101] = 0;
   out_7004170523943837202[102] = 0;
   out_7004170523943837202[103] = 0;
   out_7004170523943837202[104] = dt;
   out_7004170523943837202[105] = 0;
   out_7004170523943837202[106] = 0;
   out_7004170523943837202[107] = 0;
   out_7004170523943837202[108] = 0;
   out_7004170523943837202[109] = 0;
   out_7004170523943837202[110] = 0;
   out_7004170523943837202[111] = 0;
   out_7004170523943837202[112] = 0;
   out_7004170523943837202[113] = 0;
   out_7004170523943837202[114] = 1;
   out_7004170523943837202[115] = 0;
   out_7004170523943837202[116] = 0;
   out_7004170523943837202[117] = 0;
   out_7004170523943837202[118] = 0;
   out_7004170523943837202[119] = 0;
   out_7004170523943837202[120] = 0;
   out_7004170523943837202[121] = 0;
   out_7004170523943837202[122] = 0;
   out_7004170523943837202[123] = 0;
   out_7004170523943837202[124] = 0;
   out_7004170523943837202[125] = 0;
   out_7004170523943837202[126] = 0;
   out_7004170523943837202[127] = 0;
   out_7004170523943837202[128] = 0;
   out_7004170523943837202[129] = 0;
   out_7004170523943837202[130] = 0;
   out_7004170523943837202[131] = 0;
   out_7004170523943837202[132] = 0;
   out_7004170523943837202[133] = 1;
   out_7004170523943837202[134] = 0;
   out_7004170523943837202[135] = 0;
   out_7004170523943837202[136] = 0;
   out_7004170523943837202[137] = 0;
   out_7004170523943837202[138] = 0;
   out_7004170523943837202[139] = 0;
   out_7004170523943837202[140] = 0;
   out_7004170523943837202[141] = 0;
   out_7004170523943837202[142] = 0;
   out_7004170523943837202[143] = 0;
   out_7004170523943837202[144] = 0;
   out_7004170523943837202[145] = 0;
   out_7004170523943837202[146] = 0;
   out_7004170523943837202[147] = 0;
   out_7004170523943837202[148] = 0;
   out_7004170523943837202[149] = 0;
   out_7004170523943837202[150] = 0;
   out_7004170523943837202[151] = 0;
   out_7004170523943837202[152] = 1;
   out_7004170523943837202[153] = 0;
   out_7004170523943837202[154] = 0;
   out_7004170523943837202[155] = 0;
   out_7004170523943837202[156] = 0;
   out_7004170523943837202[157] = 0;
   out_7004170523943837202[158] = 0;
   out_7004170523943837202[159] = 0;
   out_7004170523943837202[160] = 0;
   out_7004170523943837202[161] = 0;
   out_7004170523943837202[162] = 0;
   out_7004170523943837202[163] = 0;
   out_7004170523943837202[164] = 0;
   out_7004170523943837202[165] = 0;
   out_7004170523943837202[166] = 0;
   out_7004170523943837202[167] = 0;
   out_7004170523943837202[168] = 0;
   out_7004170523943837202[169] = 0;
   out_7004170523943837202[170] = 0;
   out_7004170523943837202[171] = 1;
   out_7004170523943837202[172] = 0;
   out_7004170523943837202[173] = 0;
   out_7004170523943837202[174] = 0;
   out_7004170523943837202[175] = 0;
   out_7004170523943837202[176] = 0;
   out_7004170523943837202[177] = 0;
   out_7004170523943837202[178] = 0;
   out_7004170523943837202[179] = 0;
   out_7004170523943837202[180] = 0;
   out_7004170523943837202[181] = 0;
   out_7004170523943837202[182] = 0;
   out_7004170523943837202[183] = 0;
   out_7004170523943837202[184] = 0;
   out_7004170523943837202[185] = 0;
   out_7004170523943837202[186] = 0;
   out_7004170523943837202[187] = 0;
   out_7004170523943837202[188] = 0;
   out_7004170523943837202[189] = 0;
   out_7004170523943837202[190] = 1;
   out_7004170523943837202[191] = 0;
   out_7004170523943837202[192] = 0;
   out_7004170523943837202[193] = 0;
   out_7004170523943837202[194] = 0;
   out_7004170523943837202[195] = 0;
   out_7004170523943837202[196] = 0;
   out_7004170523943837202[197] = 0;
   out_7004170523943837202[198] = 0;
   out_7004170523943837202[199] = 0;
   out_7004170523943837202[200] = 0;
   out_7004170523943837202[201] = 0;
   out_7004170523943837202[202] = 0;
   out_7004170523943837202[203] = 0;
   out_7004170523943837202[204] = 0;
   out_7004170523943837202[205] = 0;
   out_7004170523943837202[206] = 0;
   out_7004170523943837202[207] = 0;
   out_7004170523943837202[208] = 0;
   out_7004170523943837202[209] = 1;
   out_7004170523943837202[210] = 0;
   out_7004170523943837202[211] = 0;
   out_7004170523943837202[212] = 0;
   out_7004170523943837202[213] = 0;
   out_7004170523943837202[214] = 0;
   out_7004170523943837202[215] = 0;
   out_7004170523943837202[216] = 0;
   out_7004170523943837202[217] = 0;
   out_7004170523943837202[218] = 0;
   out_7004170523943837202[219] = 0;
   out_7004170523943837202[220] = 0;
   out_7004170523943837202[221] = 0;
   out_7004170523943837202[222] = 0;
   out_7004170523943837202[223] = 0;
   out_7004170523943837202[224] = 0;
   out_7004170523943837202[225] = 0;
   out_7004170523943837202[226] = 0;
   out_7004170523943837202[227] = 0;
   out_7004170523943837202[228] = 1;
   out_7004170523943837202[229] = 0;
   out_7004170523943837202[230] = 0;
   out_7004170523943837202[231] = 0;
   out_7004170523943837202[232] = 0;
   out_7004170523943837202[233] = 0;
   out_7004170523943837202[234] = 0;
   out_7004170523943837202[235] = 0;
   out_7004170523943837202[236] = 0;
   out_7004170523943837202[237] = 0;
   out_7004170523943837202[238] = 0;
   out_7004170523943837202[239] = 0;
   out_7004170523943837202[240] = 0;
   out_7004170523943837202[241] = 0;
   out_7004170523943837202[242] = 0;
   out_7004170523943837202[243] = 0;
   out_7004170523943837202[244] = 0;
   out_7004170523943837202[245] = 0;
   out_7004170523943837202[246] = 0;
   out_7004170523943837202[247] = 1;
   out_7004170523943837202[248] = 0;
   out_7004170523943837202[249] = 0;
   out_7004170523943837202[250] = 0;
   out_7004170523943837202[251] = 0;
   out_7004170523943837202[252] = 0;
   out_7004170523943837202[253] = 0;
   out_7004170523943837202[254] = 0;
   out_7004170523943837202[255] = 0;
   out_7004170523943837202[256] = 0;
   out_7004170523943837202[257] = 0;
   out_7004170523943837202[258] = 0;
   out_7004170523943837202[259] = 0;
   out_7004170523943837202[260] = 0;
   out_7004170523943837202[261] = 0;
   out_7004170523943837202[262] = 0;
   out_7004170523943837202[263] = 0;
   out_7004170523943837202[264] = 0;
   out_7004170523943837202[265] = 0;
   out_7004170523943837202[266] = 1;
   out_7004170523943837202[267] = 0;
   out_7004170523943837202[268] = 0;
   out_7004170523943837202[269] = 0;
   out_7004170523943837202[270] = 0;
   out_7004170523943837202[271] = 0;
   out_7004170523943837202[272] = 0;
   out_7004170523943837202[273] = 0;
   out_7004170523943837202[274] = 0;
   out_7004170523943837202[275] = 0;
   out_7004170523943837202[276] = 0;
   out_7004170523943837202[277] = 0;
   out_7004170523943837202[278] = 0;
   out_7004170523943837202[279] = 0;
   out_7004170523943837202[280] = 0;
   out_7004170523943837202[281] = 0;
   out_7004170523943837202[282] = 0;
   out_7004170523943837202[283] = 0;
   out_7004170523943837202[284] = 0;
   out_7004170523943837202[285] = 1;
   out_7004170523943837202[286] = 0;
   out_7004170523943837202[287] = 0;
   out_7004170523943837202[288] = 0;
   out_7004170523943837202[289] = 0;
   out_7004170523943837202[290] = 0;
   out_7004170523943837202[291] = 0;
   out_7004170523943837202[292] = 0;
   out_7004170523943837202[293] = 0;
   out_7004170523943837202[294] = 0;
   out_7004170523943837202[295] = 0;
   out_7004170523943837202[296] = 0;
   out_7004170523943837202[297] = 0;
   out_7004170523943837202[298] = 0;
   out_7004170523943837202[299] = 0;
   out_7004170523943837202[300] = 0;
   out_7004170523943837202[301] = 0;
   out_7004170523943837202[302] = 0;
   out_7004170523943837202[303] = 0;
   out_7004170523943837202[304] = 1;
   out_7004170523943837202[305] = 0;
   out_7004170523943837202[306] = 0;
   out_7004170523943837202[307] = 0;
   out_7004170523943837202[308] = 0;
   out_7004170523943837202[309] = 0;
   out_7004170523943837202[310] = 0;
   out_7004170523943837202[311] = 0;
   out_7004170523943837202[312] = 0;
   out_7004170523943837202[313] = 0;
   out_7004170523943837202[314] = 0;
   out_7004170523943837202[315] = 0;
   out_7004170523943837202[316] = 0;
   out_7004170523943837202[317] = 0;
   out_7004170523943837202[318] = 0;
   out_7004170523943837202[319] = 0;
   out_7004170523943837202[320] = 0;
   out_7004170523943837202[321] = 0;
   out_7004170523943837202[322] = 0;
   out_7004170523943837202[323] = 1;
}
void h_4(double *state, double *unused, double *out_469880496905936735) {
   out_469880496905936735[0] = state[6] + state[9];
   out_469880496905936735[1] = state[7] + state[10];
   out_469880496905936735[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_6924153987334593695) {
   out_6924153987334593695[0] = 0;
   out_6924153987334593695[1] = 0;
   out_6924153987334593695[2] = 0;
   out_6924153987334593695[3] = 0;
   out_6924153987334593695[4] = 0;
   out_6924153987334593695[5] = 0;
   out_6924153987334593695[6] = 1;
   out_6924153987334593695[7] = 0;
   out_6924153987334593695[8] = 0;
   out_6924153987334593695[9] = 1;
   out_6924153987334593695[10] = 0;
   out_6924153987334593695[11] = 0;
   out_6924153987334593695[12] = 0;
   out_6924153987334593695[13] = 0;
   out_6924153987334593695[14] = 0;
   out_6924153987334593695[15] = 0;
   out_6924153987334593695[16] = 0;
   out_6924153987334593695[17] = 0;
   out_6924153987334593695[18] = 0;
   out_6924153987334593695[19] = 0;
   out_6924153987334593695[20] = 0;
   out_6924153987334593695[21] = 0;
   out_6924153987334593695[22] = 0;
   out_6924153987334593695[23] = 0;
   out_6924153987334593695[24] = 0;
   out_6924153987334593695[25] = 1;
   out_6924153987334593695[26] = 0;
   out_6924153987334593695[27] = 0;
   out_6924153987334593695[28] = 1;
   out_6924153987334593695[29] = 0;
   out_6924153987334593695[30] = 0;
   out_6924153987334593695[31] = 0;
   out_6924153987334593695[32] = 0;
   out_6924153987334593695[33] = 0;
   out_6924153987334593695[34] = 0;
   out_6924153987334593695[35] = 0;
   out_6924153987334593695[36] = 0;
   out_6924153987334593695[37] = 0;
   out_6924153987334593695[38] = 0;
   out_6924153987334593695[39] = 0;
   out_6924153987334593695[40] = 0;
   out_6924153987334593695[41] = 0;
   out_6924153987334593695[42] = 0;
   out_6924153987334593695[43] = 0;
   out_6924153987334593695[44] = 1;
   out_6924153987334593695[45] = 0;
   out_6924153987334593695[46] = 0;
   out_6924153987334593695[47] = 1;
   out_6924153987334593695[48] = 0;
   out_6924153987334593695[49] = 0;
   out_6924153987334593695[50] = 0;
   out_6924153987334593695[51] = 0;
   out_6924153987334593695[52] = 0;
   out_6924153987334593695[53] = 0;
}
void h_10(double *state, double *unused, double *out_7742792149057052598) {
   out_7742792149057052598[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_7742792149057052598[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_7742792149057052598[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_9199083287878354631) {
   out_9199083287878354631[0] = 0;
   out_9199083287878354631[1] = 9.8100000000000005*cos(state[1]);
   out_9199083287878354631[2] = 0;
   out_9199083287878354631[3] = 0;
   out_9199083287878354631[4] = -state[8];
   out_9199083287878354631[5] = state[7];
   out_9199083287878354631[6] = 0;
   out_9199083287878354631[7] = state[5];
   out_9199083287878354631[8] = -state[4];
   out_9199083287878354631[9] = 0;
   out_9199083287878354631[10] = 0;
   out_9199083287878354631[11] = 0;
   out_9199083287878354631[12] = 1;
   out_9199083287878354631[13] = 0;
   out_9199083287878354631[14] = 0;
   out_9199083287878354631[15] = 1;
   out_9199083287878354631[16] = 0;
   out_9199083287878354631[17] = 0;
   out_9199083287878354631[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_9199083287878354631[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_9199083287878354631[20] = 0;
   out_9199083287878354631[21] = state[8];
   out_9199083287878354631[22] = 0;
   out_9199083287878354631[23] = -state[6];
   out_9199083287878354631[24] = -state[5];
   out_9199083287878354631[25] = 0;
   out_9199083287878354631[26] = state[3];
   out_9199083287878354631[27] = 0;
   out_9199083287878354631[28] = 0;
   out_9199083287878354631[29] = 0;
   out_9199083287878354631[30] = 0;
   out_9199083287878354631[31] = 1;
   out_9199083287878354631[32] = 0;
   out_9199083287878354631[33] = 0;
   out_9199083287878354631[34] = 1;
   out_9199083287878354631[35] = 0;
   out_9199083287878354631[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_9199083287878354631[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_9199083287878354631[38] = 0;
   out_9199083287878354631[39] = -state[7];
   out_9199083287878354631[40] = state[6];
   out_9199083287878354631[41] = 0;
   out_9199083287878354631[42] = state[4];
   out_9199083287878354631[43] = -state[3];
   out_9199083287878354631[44] = 0;
   out_9199083287878354631[45] = 0;
   out_9199083287878354631[46] = 0;
   out_9199083287878354631[47] = 0;
   out_9199083287878354631[48] = 0;
   out_9199083287878354631[49] = 0;
   out_9199083287878354631[50] = 1;
   out_9199083287878354631[51] = 0;
   out_9199083287878354631[52] = 0;
   out_9199083287878354631[53] = 1;
}
void h_13(double *state, double *unused, double *out_6098920331360951697) {
   out_6098920331360951697[0] = state[3];
   out_6098920331360951697[1] = state[4];
   out_6098920331360951697[2] = state[5];
}
void H_13(double *state, double *unused, double *out_3711880162002260894) {
   out_3711880162002260894[0] = 0;
   out_3711880162002260894[1] = 0;
   out_3711880162002260894[2] = 0;
   out_3711880162002260894[3] = 1;
   out_3711880162002260894[4] = 0;
   out_3711880162002260894[5] = 0;
   out_3711880162002260894[6] = 0;
   out_3711880162002260894[7] = 0;
   out_3711880162002260894[8] = 0;
   out_3711880162002260894[9] = 0;
   out_3711880162002260894[10] = 0;
   out_3711880162002260894[11] = 0;
   out_3711880162002260894[12] = 0;
   out_3711880162002260894[13] = 0;
   out_3711880162002260894[14] = 0;
   out_3711880162002260894[15] = 0;
   out_3711880162002260894[16] = 0;
   out_3711880162002260894[17] = 0;
   out_3711880162002260894[18] = 0;
   out_3711880162002260894[19] = 0;
   out_3711880162002260894[20] = 0;
   out_3711880162002260894[21] = 0;
   out_3711880162002260894[22] = 1;
   out_3711880162002260894[23] = 0;
   out_3711880162002260894[24] = 0;
   out_3711880162002260894[25] = 0;
   out_3711880162002260894[26] = 0;
   out_3711880162002260894[27] = 0;
   out_3711880162002260894[28] = 0;
   out_3711880162002260894[29] = 0;
   out_3711880162002260894[30] = 0;
   out_3711880162002260894[31] = 0;
   out_3711880162002260894[32] = 0;
   out_3711880162002260894[33] = 0;
   out_3711880162002260894[34] = 0;
   out_3711880162002260894[35] = 0;
   out_3711880162002260894[36] = 0;
   out_3711880162002260894[37] = 0;
   out_3711880162002260894[38] = 0;
   out_3711880162002260894[39] = 0;
   out_3711880162002260894[40] = 0;
   out_3711880162002260894[41] = 1;
   out_3711880162002260894[42] = 0;
   out_3711880162002260894[43] = 0;
   out_3711880162002260894[44] = 0;
   out_3711880162002260894[45] = 0;
   out_3711880162002260894[46] = 0;
   out_3711880162002260894[47] = 0;
   out_3711880162002260894[48] = 0;
   out_3711880162002260894[49] = 0;
   out_3711880162002260894[50] = 0;
   out_3711880162002260894[51] = 0;
   out_3711880162002260894[52] = 0;
   out_3711880162002260894[53] = 0;
}
void h_14(double *state, double *unused, double *out_2194294574888024015) {
   out_2194294574888024015[0] = state[6];
   out_2194294574888024015[1] = state[7];
   out_2194294574888024015[2] = state[8];
}
void H_14(double *state, double *unused, double *out_2960913130995109166) {
   out_2960913130995109166[0] = 0;
   out_2960913130995109166[1] = 0;
   out_2960913130995109166[2] = 0;
   out_2960913130995109166[3] = 0;
   out_2960913130995109166[4] = 0;
   out_2960913130995109166[5] = 0;
   out_2960913130995109166[6] = 1;
   out_2960913130995109166[7] = 0;
   out_2960913130995109166[8] = 0;
   out_2960913130995109166[9] = 0;
   out_2960913130995109166[10] = 0;
   out_2960913130995109166[11] = 0;
   out_2960913130995109166[12] = 0;
   out_2960913130995109166[13] = 0;
   out_2960913130995109166[14] = 0;
   out_2960913130995109166[15] = 0;
   out_2960913130995109166[16] = 0;
   out_2960913130995109166[17] = 0;
   out_2960913130995109166[18] = 0;
   out_2960913130995109166[19] = 0;
   out_2960913130995109166[20] = 0;
   out_2960913130995109166[21] = 0;
   out_2960913130995109166[22] = 0;
   out_2960913130995109166[23] = 0;
   out_2960913130995109166[24] = 0;
   out_2960913130995109166[25] = 1;
   out_2960913130995109166[26] = 0;
   out_2960913130995109166[27] = 0;
   out_2960913130995109166[28] = 0;
   out_2960913130995109166[29] = 0;
   out_2960913130995109166[30] = 0;
   out_2960913130995109166[31] = 0;
   out_2960913130995109166[32] = 0;
   out_2960913130995109166[33] = 0;
   out_2960913130995109166[34] = 0;
   out_2960913130995109166[35] = 0;
   out_2960913130995109166[36] = 0;
   out_2960913130995109166[37] = 0;
   out_2960913130995109166[38] = 0;
   out_2960913130995109166[39] = 0;
   out_2960913130995109166[40] = 0;
   out_2960913130995109166[41] = 0;
   out_2960913130995109166[42] = 0;
   out_2960913130995109166[43] = 0;
   out_2960913130995109166[44] = 1;
   out_2960913130995109166[45] = 0;
   out_2960913130995109166[46] = 0;
   out_2960913130995109166[47] = 0;
   out_2960913130995109166[48] = 0;
   out_2960913130995109166[49] = 0;
   out_2960913130995109166[50] = 0;
   out_2960913130995109166[51] = 0;
   out_2960913130995109166[52] = 0;
   out_2960913130995109166[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_6044847391441660522) {
  err_fun(nom_x, delta_x, out_6044847391441660522);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5641758511196693149) {
  inv_err_fun(nom_x, true_x, out_5641758511196693149);
}
void pose_H_mod_fun(double *state, double *out_3649931908543644442) {
  H_mod_fun(state, out_3649931908543644442);
}
void pose_f_fun(double *state, double dt, double *out_1050158138610913571) {
  f_fun(state,  dt, out_1050158138610913571);
}
void pose_F_fun(double *state, double dt, double *out_7004170523943837202) {
  F_fun(state,  dt, out_7004170523943837202);
}
void pose_h_4(double *state, double *unused, double *out_469880496905936735) {
  h_4(state, unused, out_469880496905936735);
}
void pose_H_4(double *state, double *unused, double *out_6924153987334593695) {
  H_4(state, unused, out_6924153987334593695);
}
void pose_h_10(double *state, double *unused, double *out_7742792149057052598) {
  h_10(state, unused, out_7742792149057052598);
}
void pose_H_10(double *state, double *unused, double *out_9199083287878354631) {
  H_10(state, unused, out_9199083287878354631);
}
void pose_h_13(double *state, double *unused, double *out_6098920331360951697) {
  h_13(state, unused, out_6098920331360951697);
}
void pose_H_13(double *state, double *unused, double *out_3711880162002260894) {
  H_13(state, unused, out_3711880162002260894);
}
void pose_h_14(double *state, double *unused, double *out_2194294574888024015) {
  h_14(state, unused, out_2194294574888024015);
}
void pose_H_14(double *state, double *unused, double *out_2960913130995109166) {
  H_14(state, unused, out_2960913130995109166);
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
