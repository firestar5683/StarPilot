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
void err_fun(double *nom_x, double *delta_x, double *out_6369833963809703045) {
   out_6369833963809703045[0] = delta_x[0] + nom_x[0];
   out_6369833963809703045[1] = delta_x[1] + nom_x[1];
   out_6369833963809703045[2] = delta_x[2] + nom_x[2];
   out_6369833963809703045[3] = delta_x[3] + nom_x[3];
   out_6369833963809703045[4] = delta_x[4] + nom_x[4];
   out_6369833963809703045[5] = delta_x[5] + nom_x[5];
   out_6369833963809703045[6] = delta_x[6] + nom_x[6];
   out_6369833963809703045[7] = delta_x[7] + nom_x[7];
   out_6369833963809703045[8] = delta_x[8] + nom_x[8];
   out_6369833963809703045[9] = delta_x[9] + nom_x[9];
   out_6369833963809703045[10] = delta_x[10] + nom_x[10];
   out_6369833963809703045[11] = delta_x[11] + nom_x[11];
   out_6369833963809703045[12] = delta_x[12] + nom_x[12];
   out_6369833963809703045[13] = delta_x[13] + nom_x[13];
   out_6369833963809703045[14] = delta_x[14] + nom_x[14];
   out_6369833963809703045[15] = delta_x[15] + nom_x[15];
   out_6369833963809703045[16] = delta_x[16] + nom_x[16];
   out_6369833963809703045[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_4035234717988175099) {
   out_4035234717988175099[0] = -nom_x[0] + true_x[0];
   out_4035234717988175099[1] = -nom_x[1] + true_x[1];
   out_4035234717988175099[2] = -nom_x[2] + true_x[2];
   out_4035234717988175099[3] = -nom_x[3] + true_x[3];
   out_4035234717988175099[4] = -nom_x[4] + true_x[4];
   out_4035234717988175099[5] = -nom_x[5] + true_x[5];
   out_4035234717988175099[6] = -nom_x[6] + true_x[6];
   out_4035234717988175099[7] = -nom_x[7] + true_x[7];
   out_4035234717988175099[8] = -nom_x[8] + true_x[8];
   out_4035234717988175099[9] = -nom_x[9] + true_x[9];
   out_4035234717988175099[10] = -nom_x[10] + true_x[10];
   out_4035234717988175099[11] = -nom_x[11] + true_x[11];
   out_4035234717988175099[12] = -nom_x[12] + true_x[12];
   out_4035234717988175099[13] = -nom_x[13] + true_x[13];
   out_4035234717988175099[14] = -nom_x[14] + true_x[14];
   out_4035234717988175099[15] = -nom_x[15] + true_x[15];
   out_4035234717988175099[16] = -nom_x[16] + true_x[16];
   out_4035234717988175099[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_1402865724321173492) {
   out_1402865724321173492[0] = 1.0;
   out_1402865724321173492[1] = 0.0;
   out_1402865724321173492[2] = 0.0;
   out_1402865724321173492[3] = 0.0;
   out_1402865724321173492[4] = 0.0;
   out_1402865724321173492[5] = 0.0;
   out_1402865724321173492[6] = 0.0;
   out_1402865724321173492[7] = 0.0;
   out_1402865724321173492[8] = 0.0;
   out_1402865724321173492[9] = 0.0;
   out_1402865724321173492[10] = 0.0;
   out_1402865724321173492[11] = 0.0;
   out_1402865724321173492[12] = 0.0;
   out_1402865724321173492[13] = 0.0;
   out_1402865724321173492[14] = 0.0;
   out_1402865724321173492[15] = 0.0;
   out_1402865724321173492[16] = 0.0;
   out_1402865724321173492[17] = 0.0;
   out_1402865724321173492[18] = 0.0;
   out_1402865724321173492[19] = 1.0;
   out_1402865724321173492[20] = 0.0;
   out_1402865724321173492[21] = 0.0;
   out_1402865724321173492[22] = 0.0;
   out_1402865724321173492[23] = 0.0;
   out_1402865724321173492[24] = 0.0;
   out_1402865724321173492[25] = 0.0;
   out_1402865724321173492[26] = 0.0;
   out_1402865724321173492[27] = 0.0;
   out_1402865724321173492[28] = 0.0;
   out_1402865724321173492[29] = 0.0;
   out_1402865724321173492[30] = 0.0;
   out_1402865724321173492[31] = 0.0;
   out_1402865724321173492[32] = 0.0;
   out_1402865724321173492[33] = 0.0;
   out_1402865724321173492[34] = 0.0;
   out_1402865724321173492[35] = 0.0;
   out_1402865724321173492[36] = 0.0;
   out_1402865724321173492[37] = 0.0;
   out_1402865724321173492[38] = 1.0;
   out_1402865724321173492[39] = 0.0;
   out_1402865724321173492[40] = 0.0;
   out_1402865724321173492[41] = 0.0;
   out_1402865724321173492[42] = 0.0;
   out_1402865724321173492[43] = 0.0;
   out_1402865724321173492[44] = 0.0;
   out_1402865724321173492[45] = 0.0;
   out_1402865724321173492[46] = 0.0;
   out_1402865724321173492[47] = 0.0;
   out_1402865724321173492[48] = 0.0;
   out_1402865724321173492[49] = 0.0;
   out_1402865724321173492[50] = 0.0;
   out_1402865724321173492[51] = 0.0;
   out_1402865724321173492[52] = 0.0;
   out_1402865724321173492[53] = 0.0;
   out_1402865724321173492[54] = 0.0;
   out_1402865724321173492[55] = 0.0;
   out_1402865724321173492[56] = 0.0;
   out_1402865724321173492[57] = 1.0;
   out_1402865724321173492[58] = 0.0;
   out_1402865724321173492[59] = 0.0;
   out_1402865724321173492[60] = 0.0;
   out_1402865724321173492[61] = 0.0;
   out_1402865724321173492[62] = 0.0;
   out_1402865724321173492[63] = 0.0;
   out_1402865724321173492[64] = 0.0;
   out_1402865724321173492[65] = 0.0;
   out_1402865724321173492[66] = 0.0;
   out_1402865724321173492[67] = 0.0;
   out_1402865724321173492[68] = 0.0;
   out_1402865724321173492[69] = 0.0;
   out_1402865724321173492[70] = 0.0;
   out_1402865724321173492[71] = 0.0;
   out_1402865724321173492[72] = 0.0;
   out_1402865724321173492[73] = 0.0;
   out_1402865724321173492[74] = 0.0;
   out_1402865724321173492[75] = 0.0;
   out_1402865724321173492[76] = 1.0;
   out_1402865724321173492[77] = 0.0;
   out_1402865724321173492[78] = 0.0;
   out_1402865724321173492[79] = 0.0;
   out_1402865724321173492[80] = 0.0;
   out_1402865724321173492[81] = 0.0;
   out_1402865724321173492[82] = 0.0;
   out_1402865724321173492[83] = 0.0;
   out_1402865724321173492[84] = 0.0;
   out_1402865724321173492[85] = 0.0;
   out_1402865724321173492[86] = 0.0;
   out_1402865724321173492[87] = 0.0;
   out_1402865724321173492[88] = 0.0;
   out_1402865724321173492[89] = 0.0;
   out_1402865724321173492[90] = 0.0;
   out_1402865724321173492[91] = 0.0;
   out_1402865724321173492[92] = 0.0;
   out_1402865724321173492[93] = 0.0;
   out_1402865724321173492[94] = 0.0;
   out_1402865724321173492[95] = 1.0;
   out_1402865724321173492[96] = 0.0;
   out_1402865724321173492[97] = 0.0;
   out_1402865724321173492[98] = 0.0;
   out_1402865724321173492[99] = 0.0;
   out_1402865724321173492[100] = 0.0;
   out_1402865724321173492[101] = 0.0;
   out_1402865724321173492[102] = 0.0;
   out_1402865724321173492[103] = 0.0;
   out_1402865724321173492[104] = 0.0;
   out_1402865724321173492[105] = 0.0;
   out_1402865724321173492[106] = 0.0;
   out_1402865724321173492[107] = 0.0;
   out_1402865724321173492[108] = 0.0;
   out_1402865724321173492[109] = 0.0;
   out_1402865724321173492[110] = 0.0;
   out_1402865724321173492[111] = 0.0;
   out_1402865724321173492[112] = 0.0;
   out_1402865724321173492[113] = 0.0;
   out_1402865724321173492[114] = 1.0;
   out_1402865724321173492[115] = 0.0;
   out_1402865724321173492[116] = 0.0;
   out_1402865724321173492[117] = 0.0;
   out_1402865724321173492[118] = 0.0;
   out_1402865724321173492[119] = 0.0;
   out_1402865724321173492[120] = 0.0;
   out_1402865724321173492[121] = 0.0;
   out_1402865724321173492[122] = 0.0;
   out_1402865724321173492[123] = 0.0;
   out_1402865724321173492[124] = 0.0;
   out_1402865724321173492[125] = 0.0;
   out_1402865724321173492[126] = 0.0;
   out_1402865724321173492[127] = 0.0;
   out_1402865724321173492[128] = 0.0;
   out_1402865724321173492[129] = 0.0;
   out_1402865724321173492[130] = 0.0;
   out_1402865724321173492[131] = 0.0;
   out_1402865724321173492[132] = 0.0;
   out_1402865724321173492[133] = 1.0;
   out_1402865724321173492[134] = 0.0;
   out_1402865724321173492[135] = 0.0;
   out_1402865724321173492[136] = 0.0;
   out_1402865724321173492[137] = 0.0;
   out_1402865724321173492[138] = 0.0;
   out_1402865724321173492[139] = 0.0;
   out_1402865724321173492[140] = 0.0;
   out_1402865724321173492[141] = 0.0;
   out_1402865724321173492[142] = 0.0;
   out_1402865724321173492[143] = 0.0;
   out_1402865724321173492[144] = 0.0;
   out_1402865724321173492[145] = 0.0;
   out_1402865724321173492[146] = 0.0;
   out_1402865724321173492[147] = 0.0;
   out_1402865724321173492[148] = 0.0;
   out_1402865724321173492[149] = 0.0;
   out_1402865724321173492[150] = 0.0;
   out_1402865724321173492[151] = 0.0;
   out_1402865724321173492[152] = 1.0;
   out_1402865724321173492[153] = 0.0;
   out_1402865724321173492[154] = 0.0;
   out_1402865724321173492[155] = 0.0;
   out_1402865724321173492[156] = 0.0;
   out_1402865724321173492[157] = 0.0;
   out_1402865724321173492[158] = 0.0;
   out_1402865724321173492[159] = 0.0;
   out_1402865724321173492[160] = 0.0;
   out_1402865724321173492[161] = 0.0;
   out_1402865724321173492[162] = 0.0;
   out_1402865724321173492[163] = 0.0;
   out_1402865724321173492[164] = 0.0;
   out_1402865724321173492[165] = 0.0;
   out_1402865724321173492[166] = 0.0;
   out_1402865724321173492[167] = 0.0;
   out_1402865724321173492[168] = 0.0;
   out_1402865724321173492[169] = 0.0;
   out_1402865724321173492[170] = 0.0;
   out_1402865724321173492[171] = 1.0;
   out_1402865724321173492[172] = 0.0;
   out_1402865724321173492[173] = 0.0;
   out_1402865724321173492[174] = 0.0;
   out_1402865724321173492[175] = 0.0;
   out_1402865724321173492[176] = 0.0;
   out_1402865724321173492[177] = 0.0;
   out_1402865724321173492[178] = 0.0;
   out_1402865724321173492[179] = 0.0;
   out_1402865724321173492[180] = 0.0;
   out_1402865724321173492[181] = 0.0;
   out_1402865724321173492[182] = 0.0;
   out_1402865724321173492[183] = 0.0;
   out_1402865724321173492[184] = 0.0;
   out_1402865724321173492[185] = 0.0;
   out_1402865724321173492[186] = 0.0;
   out_1402865724321173492[187] = 0.0;
   out_1402865724321173492[188] = 0.0;
   out_1402865724321173492[189] = 0.0;
   out_1402865724321173492[190] = 1.0;
   out_1402865724321173492[191] = 0.0;
   out_1402865724321173492[192] = 0.0;
   out_1402865724321173492[193] = 0.0;
   out_1402865724321173492[194] = 0.0;
   out_1402865724321173492[195] = 0.0;
   out_1402865724321173492[196] = 0.0;
   out_1402865724321173492[197] = 0.0;
   out_1402865724321173492[198] = 0.0;
   out_1402865724321173492[199] = 0.0;
   out_1402865724321173492[200] = 0.0;
   out_1402865724321173492[201] = 0.0;
   out_1402865724321173492[202] = 0.0;
   out_1402865724321173492[203] = 0.0;
   out_1402865724321173492[204] = 0.0;
   out_1402865724321173492[205] = 0.0;
   out_1402865724321173492[206] = 0.0;
   out_1402865724321173492[207] = 0.0;
   out_1402865724321173492[208] = 0.0;
   out_1402865724321173492[209] = 1.0;
   out_1402865724321173492[210] = 0.0;
   out_1402865724321173492[211] = 0.0;
   out_1402865724321173492[212] = 0.0;
   out_1402865724321173492[213] = 0.0;
   out_1402865724321173492[214] = 0.0;
   out_1402865724321173492[215] = 0.0;
   out_1402865724321173492[216] = 0.0;
   out_1402865724321173492[217] = 0.0;
   out_1402865724321173492[218] = 0.0;
   out_1402865724321173492[219] = 0.0;
   out_1402865724321173492[220] = 0.0;
   out_1402865724321173492[221] = 0.0;
   out_1402865724321173492[222] = 0.0;
   out_1402865724321173492[223] = 0.0;
   out_1402865724321173492[224] = 0.0;
   out_1402865724321173492[225] = 0.0;
   out_1402865724321173492[226] = 0.0;
   out_1402865724321173492[227] = 0.0;
   out_1402865724321173492[228] = 1.0;
   out_1402865724321173492[229] = 0.0;
   out_1402865724321173492[230] = 0.0;
   out_1402865724321173492[231] = 0.0;
   out_1402865724321173492[232] = 0.0;
   out_1402865724321173492[233] = 0.0;
   out_1402865724321173492[234] = 0.0;
   out_1402865724321173492[235] = 0.0;
   out_1402865724321173492[236] = 0.0;
   out_1402865724321173492[237] = 0.0;
   out_1402865724321173492[238] = 0.0;
   out_1402865724321173492[239] = 0.0;
   out_1402865724321173492[240] = 0.0;
   out_1402865724321173492[241] = 0.0;
   out_1402865724321173492[242] = 0.0;
   out_1402865724321173492[243] = 0.0;
   out_1402865724321173492[244] = 0.0;
   out_1402865724321173492[245] = 0.0;
   out_1402865724321173492[246] = 0.0;
   out_1402865724321173492[247] = 1.0;
   out_1402865724321173492[248] = 0.0;
   out_1402865724321173492[249] = 0.0;
   out_1402865724321173492[250] = 0.0;
   out_1402865724321173492[251] = 0.0;
   out_1402865724321173492[252] = 0.0;
   out_1402865724321173492[253] = 0.0;
   out_1402865724321173492[254] = 0.0;
   out_1402865724321173492[255] = 0.0;
   out_1402865724321173492[256] = 0.0;
   out_1402865724321173492[257] = 0.0;
   out_1402865724321173492[258] = 0.0;
   out_1402865724321173492[259] = 0.0;
   out_1402865724321173492[260] = 0.0;
   out_1402865724321173492[261] = 0.0;
   out_1402865724321173492[262] = 0.0;
   out_1402865724321173492[263] = 0.0;
   out_1402865724321173492[264] = 0.0;
   out_1402865724321173492[265] = 0.0;
   out_1402865724321173492[266] = 1.0;
   out_1402865724321173492[267] = 0.0;
   out_1402865724321173492[268] = 0.0;
   out_1402865724321173492[269] = 0.0;
   out_1402865724321173492[270] = 0.0;
   out_1402865724321173492[271] = 0.0;
   out_1402865724321173492[272] = 0.0;
   out_1402865724321173492[273] = 0.0;
   out_1402865724321173492[274] = 0.0;
   out_1402865724321173492[275] = 0.0;
   out_1402865724321173492[276] = 0.0;
   out_1402865724321173492[277] = 0.0;
   out_1402865724321173492[278] = 0.0;
   out_1402865724321173492[279] = 0.0;
   out_1402865724321173492[280] = 0.0;
   out_1402865724321173492[281] = 0.0;
   out_1402865724321173492[282] = 0.0;
   out_1402865724321173492[283] = 0.0;
   out_1402865724321173492[284] = 0.0;
   out_1402865724321173492[285] = 1.0;
   out_1402865724321173492[286] = 0.0;
   out_1402865724321173492[287] = 0.0;
   out_1402865724321173492[288] = 0.0;
   out_1402865724321173492[289] = 0.0;
   out_1402865724321173492[290] = 0.0;
   out_1402865724321173492[291] = 0.0;
   out_1402865724321173492[292] = 0.0;
   out_1402865724321173492[293] = 0.0;
   out_1402865724321173492[294] = 0.0;
   out_1402865724321173492[295] = 0.0;
   out_1402865724321173492[296] = 0.0;
   out_1402865724321173492[297] = 0.0;
   out_1402865724321173492[298] = 0.0;
   out_1402865724321173492[299] = 0.0;
   out_1402865724321173492[300] = 0.0;
   out_1402865724321173492[301] = 0.0;
   out_1402865724321173492[302] = 0.0;
   out_1402865724321173492[303] = 0.0;
   out_1402865724321173492[304] = 1.0;
   out_1402865724321173492[305] = 0.0;
   out_1402865724321173492[306] = 0.0;
   out_1402865724321173492[307] = 0.0;
   out_1402865724321173492[308] = 0.0;
   out_1402865724321173492[309] = 0.0;
   out_1402865724321173492[310] = 0.0;
   out_1402865724321173492[311] = 0.0;
   out_1402865724321173492[312] = 0.0;
   out_1402865724321173492[313] = 0.0;
   out_1402865724321173492[314] = 0.0;
   out_1402865724321173492[315] = 0.0;
   out_1402865724321173492[316] = 0.0;
   out_1402865724321173492[317] = 0.0;
   out_1402865724321173492[318] = 0.0;
   out_1402865724321173492[319] = 0.0;
   out_1402865724321173492[320] = 0.0;
   out_1402865724321173492[321] = 0.0;
   out_1402865724321173492[322] = 0.0;
   out_1402865724321173492[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6035351479955239512) {
   out_6035351479955239512[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6035351479955239512[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6035351479955239512[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6035351479955239512[3] = dt*state[12] + state[3];
   out_6035351479955239512[4] = dt*state[13] + state[4];
   out_6035351479955239512[5] = dt*state[14] + state[5];
   out_6035351479955239512[6] = state[6];
   out_6035351479955239512[7] = state[7];
   out_6035351479955239512[8] = state[8];
   out_6035351479955239512[9] = state[9];
   out_6035351479955239512[10] = state[10];
   out_6035351479955239512[11] = state[11];
   out_6035351479955239512[12] = state[12];
   out_6035351479955239512[13] = state[13];
   out_6035351479955239512[14] = state[14];
   out_6035351479955239512[15] = state[15];
   out_6035351479955239512[16] = state[16];
   out_6035351479955239512[17] = state[17];
}
void F_fun(double *state, double dt, double *out_4841453483990746406) {
   out_4841453483990746406[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4841453483990746406[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4841453483990746406[2] = 0;
   out_4841453483990746406[3] = 0;
   out_4841453483990746406[4] = 0;
   out_4841453483990746406[5] = 0;
   out_4841453483990746406[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4841453483990746406[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4841453483990746406[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4841453483990746406[9] = 0;
   out_4841453483990746406[10] = 0;
   out_4841453483990746406[11] = 0;
   out_4841453483990746406[12] = 0;
   out_4841453483990746406[13] = 0;
   out_4841453483990746406[14] = 0;
   out_4841453483990746406[15] = 0;
   out_4841453483990746406[16] = 0;
   out_4841453483990746406[17] = 0;
   out_4841453483990746406[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4841453483990746406[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4841453483990746406[20] = 0;
   out_4841453483990746406[21] = 0;
   out_4841453483990746406[22] = 0;
   out_4841453483990746406[23] = 0;
   out_4841453483990746406[24] = 0;
   out_4841453483990746406[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4841453483990746406[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4841453483990746406[27] = 0;
   out_4841453483990746406[28] = 0;
   out_4841453483990746406[29] = 0;
   out_4841453483990746406[30] = 0;
   out_4841453483990746406[31] = 0;
   out_4841453483990746406[32] = 0;
   out_4841453483990746406[33] = 0;
   out_4841453483990746406[34] = 0;
   out_4841453483990746406[35] = 0;
   out_4841453483990746406[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4841453483990746406[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4841453483990746406[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4841453483990746406[39] = 0;
   out_4841453483990746406[40] = 0;
   out_4841453483990746406[41] = 0;
   out_4841453483990746406[42] = 0;
   out_4841453483990746406[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4841453483990746406[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4841453483990746406[45] = 0;
   out_4841453483990746406[46] = 0;
   out_4841453483990746406[47] = 0;
   out_4841453483990746406[48] = 0;
   out_4841453483990746406[49] = 0;
   out_4841453483990746406[50] = 0;
   out_4841453483990746406[51] = 0;
   out_4841453483990746406[52] = 0;
   out_4841453483990746406[53] = 0;
   out_4841453483990746406[54] = 0;
   out_4841453483990746406[55] = 0;
   out_4841453483990746406[56] = 0;
   out_4841453483990746406[57] = 1;
   out_4841453483990746406[58] = 0;
   out_4841453483990746406[59] = 0;
   out_4841453483990746406[60] = 0;
   out_4841453483990746406[61] = 0;
   out_4841453483990746406[62] = 0;
   out_4841453483990746406[63] = 0;
   out_4841453483990746406[64] = 0;
   out_4841453483990746406[65] = 0;
   out_4841453483990746406[66] = dt;
   out_4841453483990746406[67] = 0;
   out_4841453483990746406[68] = 0;
   out_4841453483990746406[69] = 0;
   out_4841453483990746406[70] = 0;
   out_4841453483990746406[71] = 0;
   out_4841453483990746406[72] = 0;
   out_4841453483990746406[73] = 0;
   out_4841453483990746406[74] = 0;
   out_4841453483990746406[75] = 0;
   out_4841453483990746406[76] = 1;
   out_4841453483990746406[77] = 0;
   out_4841453483990746406[78] = 0;
   out_4841453483990746406[79] = 0;
   out_4841453483990746406[80] = 0;
   out_4841453483990746406[81] = 0;
   out_4841453483990746406[82] = 0;
   out_4841453483990746406[83] = 0;
   out_4841453483990746406[84] = 0;
   out_4841453483990746406[85] = dt;
   out_4841453483990746406[86] = 0;
   out_4841453483990746406[87] = 0;
   out_4841453483990746406[88] = 0;
   out_4841453483990746406[89] = 0;
   out_4841453483990746406[90] = 0;
   out_4841453483990746406[91] = 0;
   out_4841453483990746406[92] = 0;
   out_4841453483990746406[93] = 0;
   out_4841453483990746406[94] = 0;
   out_4841453483990746406[95] = 1;
   out_4841453483990746406[96] = 0;
   out_4841453483990746406[97] = 0;
   out_4841453483990746406[98] = 0;
   out_4841453483990746406[99] = 0;
   out_4841453483990746406[100] = 0;
   out_4841453483990746406[101] = 0;
   out_4841453483990746406[102] = 0;
   out_4841453483990746406[103] = 0;
   out_4841453483990746406[104] = dt;
   out_4841453483990746406[105] = 0;
   out_4841453483990746406[106] = 0;
   out_4841453483990746406[107] = 0;
   out_4841453483990746406[108] = 0;
   out_4841453483990746406[109] = 0;
   out_4841453483990746406[110] = 0;
   out_4841453483990746406[111] = 0;
   out_4841453483990746406[112] = 0;
   out_4841453483990746406[113] = 0;
   out_4841453483990746406[114] = 1;
   out_4841453483990746406[115] = 0;
   out_4841453483990746406[116] = 0;
   out_4841453483990746406[117] = 0;
   out_4841453483990746406[118] = 0;
   out_4841453483990746406[119] = 0;
   out_4841453483990746406[120] = 0;
   out_4841453483990746406[121] = 0;
   out_4841453483990746406[122] = 0;
   out_4841453483990746406[123] = 0;
   out_4841453483990746406[124] = 0;
   out_4841453483990746406[125] = 0;
   out_4841453483990746406[126] = 0;
   out_4841453483990746406[127] = 0;
   out_4841453483990746406[128] = 0;
   out_4841453483990746406[129] = 0;
   out_4841453483990746406[130] = 0;
   out_4841453483990746406[131] = 0;
   out_4841453483990746406[132] = 0;
   out_4841453483990746406[133] = 1;
   out_4841453483990746406[134] = 0;
   out_4841453483990746406[135] = 0;
   out_4841453483990746406[136] = 0;
   out_4841453483990746406[137] = 0;
   out_4841453483990746406[138] = 0;
   out_4841453483990746406[139] = 0;
   out_4841453483990746406[140] = 0;
   out_4841453483990746406[141] = 0;
   out_4841453483990746406[142] = 0;
   out_4841453483990746406[143] = 0;
   out_4841453483990746406[144] = 0;
   out_4841453483990746406[145] = 0;
   out_4841453483990746406[146] = 0;
   out_4841453483990746406[147] = 0;
   out_4841453483990746406[148] = 0;
   out_4841453483990746406[149] = 0;
   out_4841453483990746406[150] = 0;
   out_4841453483990746406[151] = 0;
   out_4841453483990746406[152] = 1;
   out_4841453483990746406[153] = 0;
   out_4841453483990746406[154] = 0;
   out_4841453483990746406[155] = 0;
   out_4841453483990746406[156] = 0;
   out_4841453483990746406[157] = 0;
   out_4841453483990746406[158] = 0;
   out_4841453483990746406[159] = 0;
   out_4841453483990746406[160] = 0;
   out_4841453483990746406[161] = 0;
   out_4841453483990746406[162] = 0;
   out_4841453483990746406[163] = 0;
   out_4841453483990746406[164] = 0;
   out_4841453483990746406[165] = 0;
   out_4841453483990746406[166] = 0;
   out_4841453483990746406[167] = 0;
   out_4841453483990746406[168] = 0;
   out_4841453483990746406[169] = 0;
   out_4841453483990746406[170] = 0;
   out_4841453483990746406[171] = 1;
   out_4841453483990746406[172] = 0;
   out_4841453483990746406[173] = 0;
   out_4841453483990746406[174] = 0;
   out_4841453483990746406[175] = 0;
   out_4841453483990746406[176] = 0;
   out_4841453483990746406[177] = 0;
   out_4841453483990746406[178] = 0;
   out_4841453483990746406[179] = 0;
   out_4841453483990746406[180] = 0;
   out_4841453483990746406[181] = 0;
   out_4841453483990746406[182] = 0;
   out_4841453483990746406[183] = 0;
   out_4841453483990746406[184] = 0;
   out_4841453483990746406[185] = 0;
   out_4841453483990746406[186] = 0;
   out_4841453483990746406[187] = 0;
   out_4841453483990746406[188] = 0;
   out_4841453483990746406[189] = 0;
   out_4841453483990746406[190] = 1;
   out_4841453483990746406[191] = 0;
   out_4841453483990746406[192] = 0;
   out_4841453483990746406[193] = 0;
   out_4841453483990746406[194] = 0;
   out_4841453483990746406[195] = 0;
   out_4841453483990746406[196] = 0;
   out_4841453483990746406[197] = 0;
   out_4841453483990746406[198] = 0;
   out_4841453483990746406[199] = 0;
   out_4841453483990746406[200] = 0;
   out_4841453483990746406[201] = 0;
   out_4841453483990746406[202] = 0;
   out_4841453483990746406[203] = 0;
   out_4841453483990746406[204] = 0;
   out_4841453483990746406[205] = 0;
   out_4841453483990746406[206] = 0;
   out_4841453483990746406[207] = 0;
   out_4841453483990746406[208] = 0;
   out_4841453483990746406[209] = 1;
   out_4841453483990746406[210] = 0;
   out_4841453483990746406[211] = 0;
   out_4841453483990746406[212] = 0;
   out_4841453483990746406[213] = 0;
   out_4841453483990746406[214] = 0;
   out_4841453483990746406[215] = 0;
   out_4841453483990746406[216] = 0;
   out_4841453483990746406[217] = 0;
   out_4841453483990746406[218] = 0;
   out_4841453483990746406[219] = 0;
   out_4841453483990746406[220] = 0;
   out_4841453483990746406[221] = 0;
   out_4841453483990746406[222] = 0;
   out_4841453483990746406[223] = 0;
   out_4841453483990746406[224] = 0;
   out_4841453483990746406[225] = 0;
   out_4841453483990746406[226] = 0;
   out_4841453483990746406[227] = 0;
   out_4841453483990746406[228] = 1;
   out_4841453483990746406[229] = 0;
   out_4841453483990746406[230] = 0;
   out_4841453483990746406[231] = 0;
   out_4841453483990746406[232] = 0;
   out_4841453483990746406[233] = 0;
   out_4841453483990746406[234] = 0;
   out_4841453483990746406[235] = 0;
   out_4841453483990746406[236] = 0;
   out_4841453483990746406[237] = 0;
   out_4841453483990746406[238] = 0;
   out_4841453483990746406[239] = 0;
   out_4841453483990746406[240] = 0;
   out_4841453483990746406[241] = 0;
   out_4841453483990746406[242] = 0;
   out_4841453483990746406[243] = 0;
   out_4841453483990746406[244] = 0;
   out_4841453483990746406[245] = 0;
   out_4841453483990746406[246] = 0;
   out_4841453483990746406[247] = 1;
   out_4841453483990746406[248] = 0;
   out_4841453483990746406[249] = 0;
   out_4841453483990746406[250] = 0;
   out_4841453483990746406[251] = 0;
   out_4841453483990746406[252] = 0;
   out_4841453483990746406[253] = 0;
   out_4841453483990746406[254] = 0;
   out_4841453483990746406[255] = 0;
   out_4841453483990746406[256] = 0;
   out_4841453483990746406[257] = 0;
   out_4841453483990746406[258] = 0;
   out_4841453483990746406[259] = 0;
   out_4841453483990746406[260] = 0;
   out_4841453483990746406[261] = 0;
   out_4841453483990746406[262] = 0;
   out_4841453483990746406[263] = 0;
   out_4841453483990746406[264] = 0;
   out_4841453483990746406[265] = 0;
   out_4841453483990746406[266] = 1;
   out_4841453483990746406[267] = 0;
   out_4841453483990746406[268] = 0;
   out_4841453483990746406[269] = 0;
   out_4841453483990746406[270] = 0;
   out_4841453483990746406[271] = 0;
   out_4841453483990746406[272] = 0;
   out_4841453483990746406[273] = 0;
   out_4841453483990746406[274] = 0;
   out_4841453483990746406[275] = 0;
   out_4841453483990746406[276] = 0;
   out_4841453483990746406[277] = 0;
   out_4841453483990746406[278] = 0;
   out_4841453483990746406[279] = 0;
   out_4841453483990746406[280] = 0;
   out_4841453483990746406[281] = 0;
   out_4841453483990746406[282] = 0;
   out_4841453483990746406[283] = 0;
   out_4841453483990746406[284] = 0;
   out_4841453483990746406[285] = 1;
   out_4841453483990746406[286] = 0;
   out_4841453483990746406[287] = 0;
   out_4841453483990746406[288] = 0;
   out_4841453483990746406[289] = 0;
   out_4841453483990746406[290] = 0;
   out_4841453483990746406[291] = 0;
   out_4841453483990746406[292] = 0;
   out_4841453483990746406[293] = 0;
   out_4841453483990746406[294] = 0;
   out_4841453483990746406[295] = 0;
   out_4841453483990746406[296] = 0;
   out_4841453483990746406[297] = 0;
   out_4841453483990746406[298] = 0;
   out_4841453483990746406[299] = 0;
   out_4841453483990746406[300] = 0;
   out_4841453483990746406[301] = 0;
   out_4841453483990746406[302] = 0;
   out_4841453483990746406[303] = 0;
   out_4841453483990746406[304] = 1;
   out_4841453483990746406[305] = 0;
   out_4841453483990746406[306] = 0;
   out_4841453483990746406[307] = 0;
   out_4841453483990746406[308] = 0;
   out_4841453483990746406[309] = 0;
   out_4841453483990746406[310] = 0;
   out_4841453483990746406[311] = 0;
   out_4841453483990746406[312] = 0;
   out_4841453483990746406[313] = 0;
   out_4841453483990746406[314] = 0;
   out_4841453483990746406[315] = 0;
   out_4841453483990746406[316] = 0;
   out_4841453483990746406[317] = 0;
   out_4841453483990746406[318] = 0;
   out_4841453483990746406[319] = 0;
   out_4841453483990746406[320] = 0;
   out_4841453483990746406[321] = 0;
   out_4841453483990746406[322] = 0;
   out_4841453483990746406[323] = 1;
}
void h_4(double *state, double *unused, double *out_3927517291904970746) {
   out_3927517291904970746[0] = state[6] + state[9];
   out_3927517291904970746[1] = state[7] + state[10];
   out_3927517291904970746[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_648704722266460885) {
   out_648704722266460885[0] = 0;
   out_648704722266460885[1] = 0;
   out_648704722266460885[2] = 0;
   out_648704722266460885[3] = 0;
   out_648704722266460885[4] = 0;
   out_648704722266460885[5] = 0;
   out_648704722266460885[6] = 1;
   out_648704722266460885[7] = 0;
   out_648704722266460885[8] = 0;
   out_648704722266460885[9] = 1;
   out_648704722266460885[10] = 0;
   out_648704722266460885[11] = 0;
   out_648704722266460885[12] = 0;
   out_648704722266460885[13] = 0;
   out_648704722266460885[14] = 0;
   out_648704722266460885[15] = 0;
   out_648704722266460885[16] = 0;
   out_648704722266460885[17] = 0;
   out_648704722266460885[18] = 0;
   out_648704722266460885[19] = 0;
   out_648704722266460885[20] = 0;
   out_648704722266460885[21] = 0;
   out_648704722266460885[22] = 0;
   out_648704722266460885[23] = 0;
   out_648704722266460885[24] = 0;
   out_648704722266460885[25] = 1;
   out_648704722266460885[26] = 0;
   out_648704722266460885[27] = 0;
   out_648704722266460885[28] = 1;
   out_648704722266460885[29] = 0;
   out_648704722266460885[30] = 0;
   out_648704722266460885[31] = 0;
   out_648704722266460885[32] = 0;
   out_648704722266460885[33] = 0;
   out_648704722266460885[34] = 0;
   out_648704722266460885[35] = 0;
   out_648704722266460885[36] = 0;
   out_648704722266460885[37] = 0;
   out_648704722266460885[38] = 0;
   out_648704722266460885[39] = 0;
   out_648704722266460885[40] = 0;
   out_648704722266460885[41] = 0;
   out_648704722266460885[42] = 0;
   out_648704722266460885[43] = 0;
   out_648704722266460885[44] = 1;
   out_648704722266460885[45] = 0;
   out_648704722266460885[46] = 0;
   out_648704722266460885[47] = 1;
   out_648704722266460885[48] = 0;
   out_648704722266460885[49] = 0;
   out_648704722266460885[50] = 0;
   out_648704722266460885[51] = 0;
   out_648704722266460885[52] = 0;
   out_648704722266460885[53] = 0;
}
void h_10(double *state, double *unused, double *out_6439648934382479816) {
   out_6439648934382479816[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_6439648934382479816[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_6439648934382479816[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_4788307442778779812) {
   out_4788307442778779812[0] = 0;
   out_4788307442778779812[1] = 9.8100000000000005*cos(state[1]);
   out_4788307442778779812[2] = 0;
   out_4788307442778779812[3] = 0;
   out_4788307442778779812[4] = -state[8];
   out_4788307442778779812[5] = state[7];
   out_4788307442778779812[6] = 0;
   out_4788307442778779812[7] = state[5];
   out_4788307442778779812[8] = -state[4];
   out_4788307442778779812[9] = 0;
   out_4788307442778779812[10] = 0;
   out_4788307442778779812[11] = 0;
   out_4788307442778779812[12] = 1;
   out_4788307442778779812[13] = 0;
   out_4788307442778779812[14] = 0;
   out_4788307442778779812[15] = 1;
   out_4788307442778779812[16] = 0;
   out_4788307442778779812[17] = 0;
   out_4788307442778779812[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_4788307442778779812[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_4788307442778779812[20] = 0;
   out_4788307442778779812[21] = state[8];
   out_4788307442778779812[22] = 0;
   out_4788307442778779812[23] = -state[6];
   out_4788307442778779812[24] = -state[5];
   out_4788307442778779812[25] = 0;
   out_4788307442778779812[26] = state[3];
   out_4788307442778779812[27] = 0;
   out_4788307442778779812[28] = 0;
   out_4788307442778779812[29] = 0;
   out_4788307442778779812[30] = 0;
   out_4788307442778779812[31] = 1;
   out_4788307442778779812[32] = 0;
   out_4788307442778779812[33] = 0;
   out_4788307442778779812[34] = 1;
   out_4788307442778779812[35] = 0;
   out_4788307442778779812[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_4788307442778779812[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_4788307442778779812[38] = 0;
   out_4788307442778779812[39] = -state[7];
   out_4788307442778779812[40] = state[6];
   out_4788307442778779812[41] = 0;
   out_4788307442778779812[42] = state[4];
   out_4788307442778779812[43] = -state[3];
   out_4788307442778779812[44] = 0;
   out_4788307442778779812[45] = 0;
   out_4788307442778779812[46] = 0;
   out_4788307442778779812[47] = 0;
   out_4788307442778779812[48] = 0;
   out_4788307442778779812[49] = 0;
   out_4788307442778779812[50] = 1;
   out_4788307442778779812[51] = 0;
   out_4788307442778779812[52] = 0;
   out_4788307442778779812[53] = 1;
}
void h_13(double *state, double *unused, double *out_7496824369401694209) {
   out_7496824369401694209[0] = state[3];
   out_7496824369401694209[1] = state[4];
   out_7496824369401694209[2] = state[5];
}
void H_13(double *state, double *unused, double *out_4482460185568984909) {
   out_4482460185568984909[0] = 0;
   out_4482460185568984909[1] = 0;
   out_4482460185568984909[2] = 0;
   out_4482460185568984909[3] = 1;
   out_4482460185568984909[4] = 0;
   out_4482460185568984909[5] = 0;
   out_4482460185568984909[6] = 0;
   out_4482460185568984909[7] = 0;
   out_4482460185568984909[8] = 0;
   out_4482460185568984909[9] = 0;
   out_4482460185568984909[10] = 0;
   out_4482460185568984909[11] = 0;
   out_4482460185568984909[12] = 0;
   out_4482460185568984909[13] = 0;
   out_4482460185568984909[14] = 0;
   out_4482460185568984909[15] = 0;
   out_4482460185568984909[16] = 0;
   out_4482460185568984909[17] = 0;
   out_4482460185568984909[18] = 0;
   out_4482460185568984909[19] = 0;
   out_4482460185568984909[20] = 0;
   out_4482460185568984909[21] = 0;
   out_4482460185568984909[22] = 1;
   out_4482460185568984909[23] = 0;
   out_4482460185568984909[24] = 0;
   out_4482460185568984909[25] = 0;
   out_4482460185568984909[26] = 0;
   out_4482460185568984909[27] = 0;
   out_4482460185568984909[28] = 0;
   out_4482460185568984909[29] = 0;
   out_4482460185568984909[30] = 0;
   out_4482460185568984909[31] = 0;
   out_4482460185568984909[32] = 0;
   out_4482460185568984909[33] = 0;
   out_4482460185568984909[34] = 0;
   out_4482460185568984909[35] = 0;
   out_4482460185568984909[36] = 0;
   out_4482460185568984909[37] = 0;
   out_4482460185568984909[38] = 0;
   out_4482460185568984909[39] = 0;
   out_4482460185568984909[40] = 0;
   out_4482460185568984909[41] = 1;
   out_4482460185568984909[42] = 0;
   out_4482460185568984909[43] = 0;
   out_4482460185568984909[44] = 0;
   out_4482460185568984909[45] = 0;
   out_4482460185568984909[46] = 0;
   out_4482460185568984909[47] = 0;
   out_4482460185568984909[48] = 0;
   out_4482460185568984909[49] = 0;
   out_4482460185568984909[50] = 0;
   out_4482460185568984909[51] = 0;
   out_4482460185568984909[52] = 0;
   out_4482460185568984909[53] = 0;
}
void h_14(double *state, double *unused, double *out_6785183211401772861) {
   out_6785183211401772861[0] = state[6];
   out_6785183211401772861[1] = state[7];
   out_6785183211401772861[2] = state[8];
}
void H_14(double *state, double *unused, double *out_3731493154561833181) {
   out_3731493154561833181[0] = 0;
   out_3731493154561833181[1] = 0;
   out_3731493154561833181[2] = 0;
   out_3731493154561833181[3] = 0;
   out_3731493154561833181[4] = 0;
   out_3731493154561833181[5] = 0;
   out_3731493154561833181[6] = 1;
   out_3731493154561833181[7] = 0;
   out_3731493154561833181[8] = 0;
   out_3731493154561833181[9] = 0;
   out_3731493154561833181[10] = 0;
   out_3731493154561833181[11] = 0;
   out_3731493154561833181[12] = 0;
   out_3731493154561833181[13] = 0;
   out_3731493154561833181[14] = 0;
   out_3731493154561833181[15] = 0;
   out_3731493154561833181[16] = 0;
   out_3731493154561833181[17] = 0;
   out_3731493154561833181[18] = 0;
   out_3731493154561833181[19] = 0;
   out_3731493154561833181[20] = 0;
   out_3731493154561833181[21] = 0;
   out_3731493154561833181[22] = 0;
   out_3731493154561833181[23] = 0;
   out_3731493154561833181[24] = 0;
   out_3731493154561833181[25] = 1;
   out_3731493154561833181[26] = 0;
   out_3731493154561833181[27] = 0;
   out_3731493154561833181[28] = 0;
   out_3731493154561833181[29] = 0;
   out_3731493154561833181[30] = 0;
   out_3731493154561833181[31] = 0;
   out_3731493154561833181[32] = 0;
   out_3731493154561833181[33] = 0;
   out_3731493154561833181[34] = 0;
   out_3731493154561833181[35] = 0;
   out_3731493154561833181[36] = 0;
   out_3731493154561833181[37] = 0;
   out_3731493154561833181[38] = 0;
   out_3731493154561833181[39] = 0;
   out_3731493154561833181[40] = 0;
   out_3731493154561833181[41] = 0;
   out_3731493154561833181[42] = 0;
   out_3731493154561833181[43] = 0;
   out_3731493154561833181[44] = 1;
   out_3731493154561833181[45] = 0;
   out_3731493154561833181[46] = 0;
   out_3731493154561833181[47] = 0;
   out_3731493154561833181[48] = 0;
   out_3731493154561833181[49] = 0;
   out_3731493154561833181[50] = 0;
   out_3731493154561833181[51] = 0;
   out_3731493154561833181[52] = 0;
   out_3731493154561833181[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_6369833963809703045) {
  err_fun(nom_x, delta_x, out_6369833963809703045);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_4035234717988175099) {
  inv_err_fun(nom_x, true_x, out_4035234717988175099);
}
void pose_H_mod_fun(double *state, double *out_1402865724321173492) {
  H_mod_fun(state, out_1402865724321173492);
}
void pose_f_fun(double *state, double dt, double *out_6035351479955239512) {
  f_fun(state,  dt, out_6035351479955239512);
}
void pose_F_fun(double *state, double dt, double *out_4841453483990746406) {
  F_fun(state,  dt, out_4841453483990746406);
}
void pose_h_4(double *state, double *unused, double *out_3927517291904970746) {
  h_4(state, unused, out_3927517291904970746);
}
void pose_H_4(double *state, double *unused, double *out_648704722266460885) {
  H_4(state, unused, out_648704722266460885);
}
void pose_h_10(double *state, double *unused, double *out_6439648934382479816) {
  h_10(state, unused, out_6439648934382479816);
}
void pose_H_10(double *state, double *unused, double *out_4788307442778779812) {
  H_10(state, unused, out_4788307442778779812);
}
void pose_h_13(double *state, double *unused, double *out_7496824369401694209) {
  h_13(state, unused, out_7496824369401694209);
}
void pose_H_13(double *state, double *unused, double *out_4482460185568984909) {
  H_13(state, unused, out_4482460185568984909);
}
void pose_h_14(double *state, double *unused, double *out_6785183211401772861) {
  h_14(state, unused, out_6785183211401772861);
}
void pose_H_14(double *state, double *unused, double *out_3731493154561833181) {
  H_14(state, unused, out_3731493154561833181);
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
