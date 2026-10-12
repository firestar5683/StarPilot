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
void err_fun(double *nom_x, double *delta_x, double *out_6908032543271437367) {
   out_6908032543271437367[0] = delta_x[0] + nom_x[0];
   out_6908032543271437367[1] = delta_x[1] + nom_x[1];
   out_6908032543271437367[2] = delta_x[2] + nom_x[2];
   out_6908032543271437367[3] = delta_x[3] + nom_x[3];
   out_6908032543271437367[4] = delta_x[4] + nom_x[4];
   out_6908032543271437367[5] = delta_x[5] + nom_x[5];
   out_6908032543271437367[6] = delta_x[6] + nom_x[6];
   out_6908032543271437367[7] = delta_x[7] + nom_x[7];
   out_6908032543271437367[8] = delta_x[8] + nom_x[8];
   out_6908032543271437367[9] = delta_x[9] + nom_x[9];
   out_6908032543271437367[10] = delta_x[10] + nom_x[10];
   out_6908032543271437367[11] = delta_x[11] + nom_x[11];
   out_6908032543271437367[12] = delta_x[12] + nom_x[12];
   out_6908032543271437367[13] = delta_x[13] + nom_x[13];
   out_6908032543271437367[14] = delta_x[14] + nom_x[14];
   out_6908032543271437367[15] = delta_x[15] + nom_x[15];
   out_6908032543271437367[16] = delta_x[16] + nom_x[16];
   out_6908032543271437367[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6322019134835395929) {
   out_6322019134835395929[0] = -nom_x[0] + true_x[0];
   out_6322019134835395929[1] = -nom_x[1] + true_x[1];
   out_6322019134835395929[2] = -nom_x[2] + true_x[2];
   out_6322019134835395929[3] = -nom_x[3] + true_x[3];
   out_6322019134835395929[4] = -nom_x[4] + true_x[4];
   out_6322019134835395929[5] = -nom_x[5] + true_x[5];
   out_6322019134835395929[6] = -nom_x[6] + true_x[6];
   out_6322019134835395929[7] = -nom_x[7] + true_x[7];
   out_6322019134835395929[8] = -nom_x[8] + true_x[8];
   out_6322019134835395929[9] = -nom_x[9] + true_x[9];
   out_6322019134835395929[10] = -nom_x[10] + true_x[10];
   out_6322019134835395929[11] = -nom_x[11] + true_x[11];
   out_6322019134835395929[12] = -nom_x[12] + true_x[12];
   out_6322019134835395929[13] = -nom_x[13] + true_x[13];
   out_6322019134835395929[14] = -nom_x[14] + true_x[14];
   out_6322019134835395929[15] = -nom_x[15] + true_x[15];
   out_6322019134835395929[16] = -nom_x[16] + true_x[16];
   out_6322019134835395929[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_5045397248752443787) {
   out_5045397248752443787[0] = 1.0;
   out_5045397248752443787[1] = 0.0;
   out_5045397248752443787[2] = 0.0;
   out_5045397248752443787[3] = 0.0;
   out_5045397248752443787[4] = 0.0;
   out_5045397248752443787[5] = 0.0;
   out_5045397248752443787[6] = 0.0;
   out_5045397248752443787[7] = 0.0;
   out_5045397248752443787[8] = 0.0;
   out_5045397248752443787[9] = 0.0;
   out_5045397248752443787[10] = 0.0;
   out_5045397248752443787[11] = 0.0;
   out_5045397248752443787[12] = 0.0;
   out_5045397248752443787[13] = 0.0;
   out_5045397248752443787[14] = 0.0;
   out_5045397248752443787[15] = 0.0;
   out_5045397248752443787[16] = 0.0;
   out_5045397248752443787[17] = 0.0;
   out_5045397248752443787[18] = 0.0;
   out_5045397248752443787[19] = 1.0;
   out_5045397248752443787[20] = 0.0;
   out_5045397248752443787[21] = 0.0;
   out_5045397248752443787[22] = 0.0;
   out_5045397248752443787[23] = 0.0;
   out_5045397248752443787[24] = 0.0;
   out_5045397248752443787[25] = 0.0;
   out_5045397248752443787[26] = 0.0;
   out_5045397248752443787[27] = 0.0;
   out_5045397248752443787[28] = 0.0;
   out_5045397248752443787[29] = 0.0;
   out_5045397248752443787[30] = 0.0;
   out_5045397248752443787[31] = 0.0;
   out_5045397248752443787[32] = 0.0;
   out_5045397248752443787[33] = 0.0;
   out_5045397248752443787[34] = 0.0;
   out_5045397248752443787[35] = 0.0;
   out_5045397248752443787[36] = 0.0;
   out_5045397248752443787[37] = 0.0;
   out_5045397248752443787[38] = 1.0;
   out_5045397248752443787[39] = 0.0;
   out_5045397248752443787[40] = 0.0;
   out_5045397248752443787[41] = 0.0;
   out_5045397248752443787[42] = 0.0;
   out_5045397248752443787[43] = 0.0;
   out_5045397248752443787[44] = 0.0;
   out_5045397248752443787[45] = 0.0;
   out_5045397248752443787[46] = 0.0;
   out_5045397248752443787[47] = 0.0;
   out_5045397248752443787[48] = 0.0;
   out_5045397248752443787[49] = 0.0;
   out_5045397248752443787[50] = 0.0;
   out_5045397248752443787[51] = 0.0;
   out_5045397248752443787[52] = 0.0;
   out_5045397248752443787[53] = 0.0;
   out_5045397248752443787[54] = 0.0;
   out_5045397248752443787[55] = 0.0;
   out_5045397248752443787[56] = 0.0;
   out_5045397248752443787[57] = 1.0;
   out_5045397248752443787[58] = 0.0;
   out_5045397248752443787[59] = 0.0;
   out_5045397248752443787[60] = 0.0;
   out_5045397248752443787[61] = 0.0;
   out_5045397248752443787[62] = 0.0;
   out_5045397248752443787[63] = 0.0;
   out_5045397248752443787[64] = 0.0;
   out_5045397248752443787[65] = 0.0;
   out_5045397248752443787[66] = 0.0;
   out_5045397248752443787[67] = 0.0;
   out_5045397248752443787[68] = 0.0;
   out_5045397248752443787[69] = 0.0;
   out_5045397248752443787[70] = 0.0;
   out_5045397248752443787[71] = 0.0;
   out_5045397248752443787[72] = 0.0;
   out_5045397248752443787[73] = 0.0;
   out_5045397248752443787[74] = 0.0;
   out_5045397248752443787[75] = 0.0;
   out_5045397248752443787[76] = 1.0;
   out_5045397248752443787[77] = 0.0;
   out_5045397248752443787[78] = 0.0;
   out_5045397248752443787[79] = 0.0;
   out_5045397248752443787[80] = 0.0;
   out_5045397248752443787[81] = 0.0;
   out_5045397248752443787[82] = 0.0;
   out_5045397248752443787[83] = 0.0;
   out_5045397248752443787[84] = 0.0;
   out_5045397248752443787[85] = 0.0;
   out_5045397248752443787[86] = 0.0;
   out_5045397248752443787[87] = 0.0;
   out_5045397248752443787[88] = 0.0;
   out_5045397248752443787[89] = 0.0;
   out_5045397248752443787[90] = 0.0;
   out_5045397248752443787[91] = 0.0;
   out_5045397248752443787[92] = 0.0;
   out_5045397248752443787[93] = 0.0;
   out_5045397248752443787[94] = 0.0;
   out_5045397248752443787[95] = 1.0;
   out_5045397248752443787[96] = 0.0;
   out_5045397248752443787[97] = 0.0;
   out_5045397248752443787[98] = 0.0;
   out_5045397248752443787[99] = 0.0;
   out_5045397248752443787[100] = 0.0;
   out_5045397248752443787[101] = 0.0;
   out_5045397248752443787[102] = 0.0;
   out_5045397248752443787[103] = 0.0;
   out_5045397248752443787[104] = 0.0;
   out_5045397248752443787[105] = 0.0;
   out_5045397248752443787[106] = 0.0;
   out_5045397248752443787[107] = 0.0;
   out_5045397248752443787[108] = 0.0;
   out_5045397248752443787[109] = 0.0;
   out_5045397248752443787[110] = 0.0;
   out_5045397248752443787[111] = 0.0;
   out_5045397248752443787[112] = 0.0;
   out_5045397248752443787[113] = 0.0;
   out_5045397248752443787[114] = 1.0;
   out_5045397248752443787[115] = 0.0;
   out_5045397248752443787[116] = 0.0;
   out_5045397248752443787[117] = 0.0;
   out_5045397248752443787[118] = 0.0;
   out_5045397248752443787[119] = 0.0;
   out_5045397248752443787[120] = 0.0;
   out_5045397248752443787[121] = 0.0;
   out_5045397248752443787[122] = 0.0;
   out_5045397248752443787[123] = 0.0;
   out_5045397248752443787[124] = 0.0;
   out_5045397248752443787[125] = 0.0;
   out_5045397248752443787[126] = 0.0;
   out_5045397248752443787[127] = 0.0;
   out_5045397248752443787[128] = 0.0;
   out_5045397248752443787[129] = 0.0;
   out_5045397248752443787[130] = 0.0;
   out_5045397248752443787[131] = 0.0;
   out_5045397248752443787[132] = 0.0;
   out_5045397248752443787[133] = 1.0;
   out_5045397248752443787[134] = 0.0;
   out_5045397248752443787[135] = 0.0;
   out_5045397248752443787[136] = 0.0;
   out_5045397248752443787[137] = 0.0;
   out_5045397248752443787[138] = 0.0;
   out_5045397248752443787[139] = 0.0;
   out_5045397248752443787[140] = 0.0;
   out_5045397248752443787[141] = 0.0;
   out_5045397248752443787[142] = 0.0;
   out_5045397248752443787[143] = 0.0;
   out_5045397248752443787[144] = 0.0;
   out_5045397248752443787[145] = 0.0;
   out_5045397248752443787[146] = 0.0;
   out_5045397248752443787[147] = 0.0;
   out_5045397248752443787[148] = 0.0;
   out_5045397248752443787[149] = 0.0;
   out_5045397248752443787[150] = 0.0;
   out_5045397248752443787[151] = 0.0;
   out_5045397248752443787[152] = 1.0;
   out_5045397248752443787[153] = 0.0;
   out_5045397248752443787[154] = 0.0;
   out_5045397248752443787[155] = 0.0;
   out_5045397248752443787[156] = 0.0;
   out_5045397248752443787[157] = 0.0;
   out_5045397248752443787[158] = 0.0;
   out_5045397248752443787[159] = 0.0;
   out_5045397248752443787[160] = 0.0;
   out_5045397248752443787[161] = 0.0;
   out_5045397248752443787[162] = 0.0;
   out_5045397248752443787[163] = 0.0;
   out_5045397248752443787[164] = 0.0;
   out_5045397248752443787[165] = 0.0;
   out_5045397248752443787[166] = 0.0;
   out_5045397248752443787[167] = 0.0;
   out_5045397248752443787[168] = 0.0;
   out_5045397248752443787[169] = 0.0;
   out_5045397248752443787[170] = 0.0;
   out_5045397248752443787[171] = 1.0;
   out_5045397248752443787[172] = 0.0;
   out_5045397248752443787[173] = 0.0;
   out_5045397248752443787[174] = 0.0;
   out_5045397248752443787[175] = 0.0;
   out_5045397248752443787[176] = 0.0;
   out_5045397248752443787[177] = 0.0;
   out_5045397248752443787[178] = 0.0;
   out_5045397248752443787[179] = 0.0;
   out_5045397248752443787[180] = 0.0;
   out_5045397248752443787[181] = 0.0;
   out_5045397248752443787[182] = 0.0;
   out_5045397248752443787[183] = 0.0;
   out_5045397248752443787[184] = 0.0;
   out_5045397248752443787[185] = 0.0;
   out_5045397248752443787[186] = 0.0;
   out_5045397248752443787[187] = 0.0;
   out_5045397248752443787[188] = 0.0;
   out_5045397248752443787[189] = 0.0;
   out_5045397248752443787[190] = 1.0;
   out_5045397248752443787[191] = 0.0;
   out_5045397248752443787[192] = 0.0;
   out_5045397248752443787[193] = 0.0;
   out_5045397248752443787[194] = 0.0;
   out_5045397248752443787[195] = 0.0;
   out_5045397248752443787[196] = 0.0;
   out_5045397248752443787[197] = 0.0;
   out_5045397248752443787[198] = 0.0;
   out_5045397248752443787[199] = 0.0;
   out_5045397248752443787[200] = 0.0;
   out_5045397248752443787[201] = 0.0;
   out_5045397248752443787[202] = 0.0;
   out_5045397248752443787[203] = 0.0;
   out_5045397248752443787[204] = 0.0;
   out_5045397248752443787[205] = 0.0;
   out_5045397248752443787[206] = 0.0;
   out_5045397248752443787[207] = 0.0;
   out_5045397248752443787[208] = 0.0;
   out_5045397248752443787[209] = 1.0;
   out_5045397248752443787[210] = 0.0;
   out_5045397248752443787[211] = 0.0;
   out_5045397248752443787[212] = 0.0;
   out_5045397248752443787[213] = 0.0;
   out_5045397248752443787[214] = 0.0;
   out_5045397248752443787[215] = 0.0;
   out_5045397248752443787[216] = 0.0;
   out_5045397248752443787[217] = 0.0;
   out_5045397248752443787[218] = 0.0;
   out_5045397248752443787[219] = 0.0;
   out_5045397248752443787[220] = 0.0;
   out_5045397248752443787[221] = 0.0;
   out_5045397248752443787[222] = 0.0;
   out_5045397248752443787[223] = 0.0;
   out_5045397248752443787[224] = 0.0;
   out_5045397248752443787[225] = 0.0;
   out_5045397248752443787[226] = 0.0;
   out_5045397248752443787[227] = 0.0;
   out_5045397248752443787[228] = 1.0;
   out_5045397248752443787[229] = 0.0;
   out_5045397248752443787[230] = 0.0;
   out_5045397248752443787[231] = 0.0;
   out_5045397248752443787[232] = 0.0;
   out_5045397248752443787[233] = 0.0;
   out_5045397248752443787[234] = 0.0;
   out_5045397248752443787[235] = 0.0;
   out_5045397248752443787[236] = 0.0;
   out_5045397248752443787[237] = 0.0;
   out_5045397248752443787[238] = 0.0;
   out_5045397248752443787[239] = 0.0;
   out_5045397248752443787[240] = 0.0;
   out_5045397248752443787[241] = 0.0;
   out_5045397248752443787[242] = 0.0;
   out_5045397248752443787[243] = 0.0;
   out_5045397248752443787[244] = 0.0;
   out_5045397248752443787[245] = 0.0;
   out_5045397248752443787[246] = 0.0;
   out_5045397248752443787[247] = 1.0;
   out_5045397248752443787[248] = 0.0;
   out_5045397248752443787[249] = 0.0;
   out_5045397248752443787[250] = 0.0;
   out_5045397248752443787[251] = 0.0;
   out_5045397248752443787[252] = 0.0;
   out_5045397248752443787[253] = 0.0;
   out_5045397248752443787[254] = 0.0;
   out_5045397248752443787[255] = 0.0;
   out_5045397248752443787[256] = 0.0;
   out_5045397248752443787[257] = 0.0;
   out_5045397248752443787[258] = 0.0;
   out_5045397248752443787[259] = 0.0;
   out_5045397248752443787[260] = 0.0;
   out_5045397248752443787[261] = 0.0;
   out_5045397248752443787[262] = 0.0;
   out_5045397248752443787[263] = 0.0;
   out_5045397248752443787[264] = 0.0;
   out_5045397248752443787[265] = 0.0;
   out_5045397248752443787[266] = 1.0;
   out_5045397248752443787[267] = 0.0;
   out_5045397248752443787[268] = 0.0;
   out_5045397248752443787[269] = 0.0;
   out_5045397248752443787[270] = 0.0;
   out_5045397248752443787[271] = 0.0;
   out_5045397248752443787[272] = 0.0;
   out_5045397248752443787[273] = 0.0;
   out_5045397248752443787[274] = 0.0;
   out_5045397248752443787[275] = 0.0;
   out_5045397248752443787[276] = 0.0;
   out_5045397248752443787[277] = 0.0;
   out_5045397248752443787[278] = 0.0;
   out_5045397248752443787[279] = 0.0;
   out_5045397248752443787[280] = 0.0;
   out_5045397248752443787[281] = 0.0;
   out_5045397248752443787[282] = 0.0;
   out_5045397248752443787[283] = 0.0;
   out_5045397248752443787[284] = 0.0;
   out_5045397248752443787[285] = 1.0;
   out_5045397248752443787[286] = 0.0;
   out_5045397248752443787[287] = 0.0;
   out_5045397248752443787[288] = 0.0;
   out_5045397248752443787[289] = 0.0;
   out_5045397248752443787[290] = 0.0;
   out_5045397248752443787[291] = 0.0;
   out_5045397248752443787[292] = 0.0;
   out_5045397248752443787[293] = 0.0;
   out_5045397248752443787[294] = 0.0;
   out_5045397248752443787[295] = 0.0;
   out_5045397248752443787[296] = 0.0;
   out_5045397248752443787[297] = 0.0;
   out_5045397248752443787[298] = 0.0;
   out_5045397248752443787[299] = 0.0;
   out_5045397248752443787[300] = 0.0;
   out_5045397248752443787[301] = 0.0;
   out_5045397248752443787[302] = 0.0;
   out_5045397248752443787[303] = 0.0;
   out_5045397248752443787[304] = 1.0;
   out_5045397248752443787[305] = 0.0;
   out_5045397248752443787[306] = 0.0;
   out_5045397248752443787[307] = 0.0;
   out_5045397248752443787[308] = 0.0;
   out_5045397248752443787[309] = 0.0;
   out_5045397248752443787[310] = 0.0;
   out_5045397248752443787[311] = 0.0;
   out_5045397248752443787[312] = 0.0;
   out_5045397248752443787[313] = 0.0;
   out_5045397248752443787[314] = 0.0;
   out_5045397248752443787[315] = 0.0;
   out_5045397248752443787[316] = 0.0;
   out_5045397248752443787[317] = 0.0;
   out_5045397248752443787[318] = 0.0;
   out_5045397248752443787[319] = 0.0;
   out_5045397248752443787[320] = 0.0;
   out_5045397248752443787[321] = 0.0;
   out_5045397248752443787[322] = 0.0;
   out_5045397248752443787[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_2578103679579667045) {
   out_2578103679579667045[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_2578103679579667045[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_2578103679579667045[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_2578103679579667045[3] = dt*state[12] + state[3];
   out_2578103679579667045[4] = dt*state[13] + state[4];
   out_2578103679579667045[5] = dt*state[14] + state[5];
   out_2578103679579667045[6] = state[6];
   out_2578103679579667045[7] = state[7];
   out_2578103679579667045[8] = state[8];
   out_2578103679579667045[9] = state[9];
   out_2578103679579667045[10] = state[10];
   out_2578103679579667045[11] = state[11];
   out_2578103679579667045[12] = state[12];
   out_2578103679579667045[13] = state[13];
   out_2578103679579667045[14] = state[14];
   out_2578103679579667045[15] = state[15];
   out_2578103679579667045[16] = state[16];
   out_2578103679579667045[17] = state[17];
}
void F_fun(double *state, double dt, double *out_9023639176273047325) {
   out_9023639176273047325[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_9023639176273047325[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_9023639176273047325[2] = 0;
   out_9023639176273047325[3] = 0;
   out_9023639176273047325[4] = 0;
   out_9023639176273047325[5] = 0;
   out_9023639176273047325[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_9023639176273047325[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_9023639176273047325[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_9023639176273047325[9] = 0;
   out_9023639176273047325[10] = 0;
   out_9023639176273047325[11] = 0;
   out_9023639176273047325[12] = 0;
   out_9023639176273047325[13] = 0;
   out_9023639176273047325[14] = 0;
   out_9023639176273047325[15] = 0;
   out_9023639176273047325[16] = 0;
   out_9023639176273047325[17] = 0;
   out_9023639176273047325[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_9023639176273047325[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_9023639176273047325[20] = 0;
   out_9023639176273047325[21] = 0;
   out_9023639176273047325[22] = 0;
   out_9023639176273047325[23] = 0;
   out_9023639176273047325[24] = 0;
   out_9023639176273047325[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_9023639176273047325[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_9023639176273047325[27] = 0;
   out_9023639176273047325[28] = 0;
   out_9023639176273047325[29] = 0;
   out_9023639176273047325[30] = 0;
   out_9023639176273047325[31] = 0;
   out_9023639176273047325[32] = 0;
   out_9023639176273047325[33] = 0;
   out_9023639176273047325[34] = 0;
   out_9023639176273047325[35] = 0;
   out_9023639176273047325[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_9023639176273047325[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_9023639176273047325[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_9023639176273047325[39] = 0;
   out_9023639176273047325[40] = 0;
   out_9023639176273047325[41] = 0;
   out_9023639176273047325[42] = 0;
   out_9023639176273047325[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_9023639176273047325[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_9023639176273047325[45] = 0;
   out_9023639176273047325[46] = 0;
   out_9023639176273047325[47] = 0;
   out_9023639176273047325[48] = 0;
   out_9023639176273047325[49] = 0;
   out_9023639176273047325[50] = 0;
   out_9023639176273047325[51] = 0;
   out_9023639176273047325[52] = 0;
   out_9023639176273047325[53] = 0;
   out_9023639176273047325[54] = 0;
   out_9023639176273047325[55] = 0;
   out_9023639176273047325[56] = 0;
   out_9023639176273047325[57] = 1;
   out_9023639176273047325[58] = 0;
   out_9023639176273047325[59] = 0;
   out_9023639176273047325[60] = 0;
   out_9023639176273047325[61] = 0;
   out_9023639176273047325[62] = 0;
   out_9023639176273047325[63] = 0;
   out_9023639176273047325[64] = 0;
   out_9023639176273047325[65] = 0;
   out_9023639176273047325[66] = dt;
   out_9023639176273047325[67] = 0;
   out_9023639176273047325[68] = 0;
   out_9023639176273047325[69] = 0;
   out_9023639176273047325[70] = 0;
   out_9023639176273047325[71] = 0;
   out_9023639176273047325[72] = 0;
   out_9023639176273047325[73] = 0;
   out_9023639176273047325[74] = 0;
   out_9023639176273047325[75] = 0;
   out_9023639176273047325[76] = 1;
   out_9023639176273047325[77] = 0;
   out_9023639176273047325[78] = 0;
   out_9023639176273047325[79] = 0;
   out_9023639176273047325[80] = 0;
   out_9023639176273047325[81] = 0;
   out_9023639176273047325[82] = 0;
   out_9023639176273047325[83] = 0;
   out_9023639176273047325[84] = 0;
   out_9023639176273047325[85] = dt;
   out_9023639176273047325[86] = 0;
   out_9023639176273047325[87] = 0;
   out_9023639176273047325[88] = 0;
   out_9023639176273047325[89] = 0;
   out_9023639176273047325[90] = 0;
   out_9023639176273047325[91] = 0;
   out_9023639176273047325[92] = 0;
   out_9023639176273047325[93] = 0;
   out_9023639176273047325[94] = 0;
   out_9023639176273047325[95] = 1;
   out_9023639176273047325[96] = 0;
   out_9023639176273047325[97] = 0;
   out_9023639176273047325[98] = 0;
   out_9023639176273047325[99] = 0;
   out_9023639176273047325[100] = 0;
   out_9023639176273047325[101] = 0;
   out_9023639176273047325[102] = 0;
   out_9023639176273047325[103] = 0;
   out_9023639176273047325[104] = dt;
   out_9023639176273047325[105] = 0;
   out_9023639176273047325[106] = 0;
   out_9023639176273047325[107] = 0;
   out_9023639176273047325[108] = 0;
   out_9023639176273047325[109] = 0;
   out_9023639176273047325[110] = 0;
   out_9023639176273047325[111] = 0;
   out_9023639176273047325[112] = 0;
   out_9023639176273047325[113] = 0;
   out_9023639176273047325[114] = 1;
   out_9023639176273047325[115] = 0;
   out_9023639176273047325[116] = 0;
   out_9023639176273047325[117] = 0;
   out_9023639176273047325[118] = 0;
   out_9023639176273047325[119] = 0;
   out_9023639176273047325[120] = 0;
   out_9023639176273047325[121] = 0;
   out_9023639176273047325[122] = 0;
   out_9023639176273047325[123] = 0;
   out_9023639176273047325[124] = 0;
   out_9023639176273047325[125] = 0;
   out_9023639176273047325[126] = 0;
   out_9023639176273047325[127] = 0;
   out_9023639176273047325[128] = 0;
   out_9023639176273047325[129] = 0;
   out_9023639176273047325[130] = 0;
   out_9023639176273047325[131] = 0;
   out_9023639176273047325[132] = 0;
   out_9023639176273047325[133] = 1;
   out_9023639176273047325[134] = 0;
   out_9023639176273047325[135] = 0;
   out_9023639176273047325[136] = 0;
   out_9023639176273047325[137] = 0;
   out_9023639176273047325[138] = 0;
   out_9023639176273047325[139] = 0;
   out_9023639176273047325[140] = 0;
   out_9023639176273047325[141] = 0;
   out_9023639176273047325[142] = 0;
   out_9023639176273047325[143] = 0;
   out_9023639176273047325[144] = 0;
   out_9023639176273047325[145] = 0;
   out_9023639176273047325[146] = 0;
   out_9023639176273047325[147] = 0;
   out_9023639176273047325[148] = 0;
   out_9023639176273047325[149] = 0;
   out_9023639176273047325[150] = 0;
   out_9023639176273047325[151] = 0;
   out_9023639176273047325[152] = 1;
   out_9023639176273047325[153] = 0;
   out_9023639176273047325[154] = 0;
   out_9023639176273047325[155] = 0;
   out_9023639176273047325[156] = 0;
   out_9023639176273047325[157] = 0;
   out_9023639176273047325[158] = 0;
   out_9023639176273047325[159] = 0;
   out_9023639176273047325[160] = 0;
   out_9023639176273047325[161] = 0;
   out_9023639176273047325[162] = 0;
   out_9023639176273047325[163] = 0;
   out_9023639176273047325[164] = 0;
   out_9023639176273047325[165] = 0;
   out_9023639176273047325[166] = 0;
   out_9023639176273047325[167] = 0;
   out_9023639176273047325[168] = 0;
   out_9023639176273047325[169] = 0;
   out_9023639176273047325[170] = 0;
   out_9023639176273047325[171] = 1;
   out_9023639176273047325[172] = 0;
   out_9023639176273047325[173] = 0;
   out_9023639176273047325[174] = 0;
   out_9023639176273047325[175] = 0;
   out_9023639176273047325[176] = 0;
   out_9023639176273047325[177] = 0;
   out_9023639176273047325[178] = 0;
   out_9023639176273047325[179] = 0;
   out_9023639176273047325[180] = 0;
   out_9023639176273047325[181] = 0;
   out_9023639176273047325[182] = 0;
   out_9023639176273047325[183] = 0;
   out_9023639176273047325[184] = 0;
   out_9023639176273047325[185] = 0;
   out_9023639176273047325[186] = 0;
   out_9023639176273047325[187] = 0;
   out_9023639176273047325[188] = 0;
   out_9023639176273047325[189] = 0;
   out_9023639176273047325[190] = 1;
   out_9023639176273047325[191] = 0;
   out_9023639176273047325[192] = 0;
   out_9023639176273047325[193] = 0;
   out_9023639176273047325[194] = 0;
   out_9023639176273047325[195] = 0;
   out_9023639176273047325[196] = 0;
   out_9023639176273047325[197] = 0;
   out_9023639176273047325[198] = 0;
   out_9023639176273047325[199] = 0;
   out_9023639176273047325[200] = 0;
   out_9023639176273047325[201] = 0;
   out_9023639176273047325[202] = 0;
   out_9023639176273047325[203] = 0;
   out_9023639176273047325[204] = 0;
   out_9023639176273047325[205] = 0;
   out_9023639176273047325[206] = 0;
   out_9023639176273047325[207] = 0;
   out_9023639176273047325[208] = 0;
   out_9023639176273047325[209] = 1;
   out_9023639176273047325[210] = 0;
   out_9023639176273047325[211] = 0;
   out_9023639176273047325[212] = 0;
   out_9023639176273047325[213] = 0;
   out_9023639176273047325[214] = 0;
   out_9023639176273047325[215] = 0;
   out_9023639176273047325[216] = 0;
   out_9023639176273047325[217] = 0;
   out_9023639176273047325[218] = 0;
   out_9023639176273047325[219] = 0;
   out_9023639176273047325[220] = 0;
   out_9023639176273047325[221] = 0;
   out_9023639176273047325[222] = 0;
   out_9023639176273047325[223] = 0;
   out_9023639176273047325[224] = 0;
   out_9023639176273047325[225] = 0;
   out_9023639176273047325[226] = 0;
   out_9023639176273047325[227] = 0;
   out_9023639176273047325[228] = 1;
   out_9023639176273047325[229] = 0;
   out_9023639176273047325[230] = 0;
   out_9023639176273047325[231] = 0;
   out_9023639176273047325[232] = 0;
   out_9023639176273047325[233] = 0;
   out_9023639176273047325[234] = 0;
   out_9023639176273047325[235] = 0;
   out_9023639176273047325[236] = 0;
   out_9023639176273047325[237] = 0;
   out_9023639176273047325[238] = 0;
   out_9023639176273047325[239] = 0;
   out_9023639176273047325[240] = 0;
   out_9023639176273047325[241] = 0;
   out_9023639176273047325[242] = 0;
   out_9023639176273047325[243] = 0;
   out_9023639176273047325[244] = 0;
   out_9023639176273047325[245] = 0;
   out_9023639176273047325[246] = 0;
   out_9023639176273047325[247] = 1;
   out_9023639176273047325[248] = 0;
   out_9023639176273047325[249] = 0;
   out_9023639176273047325[250] = 0;
   out_9023639176273047325[251] = 0;
   out_9023639176273047325[252] = 0;
   out_9023639176273047325[253] = 0;
   out_9023639176273047325[254] = 0;
   out_9023639176273047325[255] = 0;
   out_9023639176273047325[256] = 0;
   out_9023639176273047325[257] = 0;
   out_9023639176273047325[258] = 0;
   out_9023639176273047325[259] = 0;
   out_9023639176273047325[260] = 0;
   out_9023639176273047325[261] = 0;
   out_9023639176273047325[262] = 0;
   out_9023639176273047325[263] = 0;
   out_9023639176273047325[264] = 0;
   out_9023639176273047325[265] = 0;
   out_9023639176273047325[266] = 1;
   out_9023639176273047325[267] = 0;
   out_9023639176273047325[268] = 0;
   out_9023639176273047325[269] = 0;
   out_9023639176273047325[270] = 0;
   out_9023639176273047325[271] = 0;
   out_9023639176273047325[272] = 0;
   out_9023639176273047325[273] = 0;
   out_9023639176273047325[274] = 0;
   out_9023639176273047325[275] = 0;
   out_9023639176273047325[276] = 0;
   out_9023639176273047325[277] = 0;
   out_9023639176273047325[278] = 0;
   out_9023639176273047325[279] = 0;
   out_9023639176273047325[280] = 0;
   out_9023639176273047325[281] = 0;
   out_9023639176273047325[282] = 0;
   out_9023639176273047325[283] = 0;
   out_9023639176273047325[284] = 0;
   out_9023639176273047325[285] = 1;
   out_9023639176273047325[286] = 0;
   out_9023639176273047325[287] = 0;
   out_9023639176273047325[288] = 0;
   out_9023639176273047325[289] = 0;
   out_9023639176273047325[290] = 0;
   out_9023639176273047325[291] = 0;
   out_9023639176273047325[292] = 0;
   out_9023639176273047325[293] = 0;
   out_9023639176273047325[294] = 0;
   out_9023639176273047325[295] = 0;
   out_9023639176273047325[296] = 0;
   out_9023639176273047325[297] = 0;
   out_9023639176273047325[298] = 0;
   out_9023639176273047325[299] = 0;
   out_9023639176273047325[300] = 0;
   out_9023639176273047325[301] = 0;
   out_9023639176273047325[302] = 0;
   out_9023639176273047325[303] = 0;
   out_9023639176273047325[304] = 1;
   out_9023639176273047325[305] = 0;
   out_9023639176273047325[306] = 0;
   out_9023639176273047325[307] = 0;
   out_9023639176273047325[308] = 0;
   out_9023639176273047325[309] = 0;
   out_9023639176273047325[310] = 0;
   out_9023639176273047325[311] = 0;
   out_9023639176273047325[312] = 0;
   out_9023639176273047325[313] = 0;
   out_9023639176273047325[314] = 0;
   out_9023639176273047325[315] = 0;
   out_9023639176273047325[316] = 0;
   out_9023639176273047325[317] = 0;
   out_9023639176273047325[318] = 0;
   out_9023639176273047325[319] = 0;
   out_9023639176273047325[320] = 0;
   out_9023639176273047325[321] = 0;
   out_9023639176273047325[322] = 0;
   out_9023639176273047325[323] = 1;
}
void h_4(double *state, double *unused, double *out_6773770520031459625) {
   out_6773770520031459625[0] = state[6] + state[9];
   out_6773770520031459625[1] = state[7] + state[10];
   out_6773770520031459625[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_4456985158899286487) {
   out_4456985158899286487[0] = 0;
   out_4456985158899286487[1] = 0;
   out_4456985158899286487[2] = 0;
   out_4456985158899286487[3] = 0;
   out_4456985158899286487[4] = 0;
   out_4456985158899286487[5] = 0;
   out_4456985158899286487[6] = 1;
   out_4456985158899286487[7] = 0;
   out_4456985158899286487[8] = 0;
   out_4456985158899286487[9] = 1;
   out_4456985158899286487[10] = 0;
   out_4456985158899286487[11] = 0;
   out_4456985158899286487[12] = 0;
   out_4456985158899286487[13] = 0;
   out_4456985158899286487[14] = 0;
   out_4456985158899286487[15] = 0;
   out_4456985158899286487[16] = 0;
   out_4456985158899286487[17] = 0;
   out_4456985158899286487[18] = 0;
   out_4456985158899286487[19] = 0;
   out_4456985158899286487[20] = 0;
   out_4456985158899286487[21] = 0;
   out_4456985158899286487[22] = 0;
   out_4456985158899286487[23] = 0;
   out_4456985158899286487[24] = 0;
   out_4456985158899286487[25] = 1;
   out_4456985158899286487[26] = 0;
   out_4456985158899286487[27] = 0;
   out_4456985158899286487[28] = 1;
   out_4456985158899286487[29] = 0;
   out_4456985158899286487[30] = 0;
   out_4456985158899286487[31] = 0;
   out_4456985158899286487[32] = 0;
   out_4456985158899286487[33] = 0;
   out_4456985158899286487[34] = 0;
   out_4456985158899286487[35] = 0;
   out_4456985158899286487[36] = 0;
   out_4456985158899286487[37] = 0;
   out_4456985158899286487[38] = 0;
   out_4456985158899286487[39] = 0;
   out_4456985158899286487[40] = 0;
   out_4456985158899286487[41] = 0;
   out_4456985158899286487[42] = 0;
   out_4456985158899286487[43] = 0;
   out_4456985158899286487[44] = 1;
   out_4456985158899286487[45] = 0;
   out_4456985158899286487[46] = 0;
   out_4456985158899286487[47] = 1;
   out_4456985158899286487[48] = 0;
   out_4456985158899286487[49] = 0;
   out_4456985158899286487[50] = 0;
   out_4456985158899286487[51] = 0;
   out_4456985158899286487[52] = 0;
   out_4456985158899286487[53] = 0;
}
void h_10(double *state, double *unused, double *out_2891796970203767629) {
   out_2891796970203767629[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_2891796970203767629[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_2891796970203767629[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_5240016567730035669) {
   out_5240016567730035669[0] = 0;
   out_5240016567730035669[1] = 9.8100000000000005*cos(state[1]);
   out_5240016567730035669[2] = 0;
   out_5240016567730035669[3] = 0;
   out_5240016567730035669[4] = -state[8];
   out_5240016567730035669[5] = state[7];
   out_5240016567730035669[6] = 0;
   out_5240016567730035669[7] = state[5];
   out_5240016567730035669[8] = -state[4];
   out_5240016567730035669[9] = 0;
   out_5240016567730035669[10] = 0;
   out_5240016567730035669[11] = 0;
   out_5240016567730035669[12] = 1;
   out_5240016567730035669[13] = 0;
   out_5240016567730035669[14] = 0;
   out_5240016567730035669[15] = 1;
   out_5240016567730035669[16] = 0;
   out_5240016567730035669[17] = 0;
   out_5240016567730035669[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_5240016567730035669[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_5240016567730035669[20] = 0;
   out_5240016567730035669[21] = state[8];
   out_5240016567730035669[22] = 0;
   out_5240016567730035669[23] = -state[6];
   out_5240016567730035669[24] = -state[5];
   out_5240016567730035669[25] = 0;
   out_5240016567730035669[26] = state[3];
   out_5240016567730035669[27] = 0;
   out_5240016567730035669[28] = 0;
   out_5240016567730035669[29] = 0;
   out_5240016567730035669[30] = 0;
   out_5240016567730035669[31] = 1;
   out_5240016567730035669[32] = 0;
   out_5240016567730035669[33] = 0;
   out_5240016567730035669[34] = 1;
   out_5240016567730035669[35] = 0;
   out_5240016567730035669[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_5240016567730035669[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_5240016567730035669[38] = 0;
   out_5240016567730035669[39] = -state[7];
   out_5240016567730035669[40] = state[6];
   out_5240016567730035669[41] = 0;
   out_5240016567730035669[42] = state[4];
   out_5240016567730035669[43] = -state[3];
   out_5240016567730035669[44] = 0;
   out_5240016567730035669[45] = 0;
   out_5240016567730035669[46] = 0;
   out_5240016567730035669[47] = 0;
   out_5240016567730035669[48] = 0;
   out_5240016567730035669[49] = 0;
   out_5240016567730035669[50] = 1;
   out_5240016567730035669[51] = 0;
   out_5240016567730035669[52] = 0;
   out_5240016567730035669[53] = 1;
}
void h_13(double *state, double *unused, double *out_7766623268738295305) {
   out_7766623268738295305[0] = state[3];
   out_7766623268738295305[1] = state[4];
   out_7766623268738295305[2] = state[5];
}
void H_13(double *state, double *unused, double *out_623229695596762463) {
   out_623229695596762463[0] = 0;
   out_623229695596762463[1] = 0;
   out_623229695596762463[2] = 0;
   out_623229695596762463[3] = 1;
   out_623229695596762463[4] = 0;
   out_623229695596762463[5] = 0;
   out_623229695596762463[6] = 0;
   out_623229695596762463[7] = 0;
   out_623229695596762463[8] = 0;
   out_623229695596762463[9] = 0;
   out_623229695596762463[10] = 0;
   out_623229695596762463[11] = 0;
   out_623229695596762463[12] = 0;
   out_623229695596762463[13] = 0;
   out_623229695596762463[14] = 0;
   out_623229695596762463[15] = 0;
   out_623229695596762463[16] = 0;
   out_623229695596762463[17] = 0;
   out_623229695596762463[18] = 0;
   out_623229695596762463[19] = 0;
   out_623229695596762463[20] = 0;
   out_623229695596762463[21] = 0;
   out_623229695596762463[22] = 1;
   out_623229695596762463[23] = 0;
   out_623229695596762463[24] = 0;
   out_623229695596762463[25] = 0;
   out_623229695596762463[26] = 0;
   out_623229695596762463[27] = 0;
   out_623229695596762463[28] = 0;
   out_623229695596762463[29] = 0;
   out_623229695596762463[30] = 0;
   out_623229695596762463[31] = 0;
   out_623229695596762463[32] = 0;
   out_623229695596762463[33] = 0;
   out_623229695596762463[34] = 0;
   out_623229695596762463[35] = 0;
   out_623229695596762463[36] = 0;
   out_623229695596762463[37] = 0;
   out_623229695596762463[38] = 0;
   out_623229695596762463[39] = 0;
   out_623229695596762463[40] = 0;
   out_623229695596762463[41] = 1;
   out_623229695596762463[42] = 0;
   out_623229695596762463[43] = 0;
   out_623229695596762463[44] = 0;
   out_623229695596762463[45] = 0;
   out_623229695596762463[46] = 0;
   out_623229695596762463[47] = 0;
   out_623229695596762463[48] = 0;
   out_623229695596762463[49] = 0;
   out_623229695596762463[50] = 0;
   out_623229695596762463[51] = 0;
   out_623229695596762463[52] = 0;
   out_623229695596762463[53] = 0;
}
void h_14(double *state, double *unused, double *out_3433693932581315158) {
   out_3433693932581315158[0] = state[6];
   out_3433693932581315158[1] = state[7];
   out_3433693932581315158[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1374196726603914191) {
   out_1374196726603914191[0] = 0;
   out_1374196726603914191[1] = 0;
   out_1374196726603914191[2] = 0;
   out_1374196726603914191[3] = 0;
   out_1374196726603914191[4] = 0;
   out_1374196726603914191[5] = 0;
   out_1374196726603914191[6] = 1;
   out_1374196726603914191[7] = 0;
   out_1374196726603914191[8] = 0;
   out_1374196726603914191[9] = 0;
   out_1374196726603914191[10] = 0;
   out_1374196726603914191[11] = 0;
   out_1374196726603914191[12] = 0;
   out_1374196726603914191[13] = 0;
   out_1374196726603914191[14] = 0;
   out_1374196726603914191[15] = 0;
   out_1374196726603914191[16] = 0;
   out_1374196726603914191[17] = 0;
   out_1374196726603914191[18] = 0;
   out_1374196726603914191[19] = 0;
   out_1374196726603914191[20] = 0;
   out_1374196726603914191[21] = 0;
   out_1374196726603914191[22] = 0;
   out_1374196726603914191[23] = 0;
   out_1374196726603914191[24] = 0;
   out_1374196726603914191[25] = 1;
   out_1374196726603914191[26] = 0;
   out_1374196726603914191[27] = 0;
   out_1374196726603914191[28] = 0;
   out_1374196726603914191[29] = 0;
   out_1374196726603914191[30] = 0;
   out_1374196726603914191[31] = 0;
   out_1374196726603914191[32] = 0;
   out_1374196726603914191[33] = 0;
   out_1374196726603914191[34] = 0;
   out_1374196726603914191[35] = 0;
   out_1374196726603914191[36] = 0;
   out_1374196726603914191[37] = 0;
   out_1374196726603914191[38] = 0;
   out_1374196726603914191[39] = 0;
   out_1374196726603914191[40] = 0;
   out_1374196726603914191[41] = 0;
   out_1374196726603914191[42] = 0;
   out_1374196726603914191[43] = 0;
   out_1374196726603914191[44] = 1;
   out_1374196726603914191[45] = 0;
   out_1374196726603914191[46] = 0;
   out_1374196726603914191[47] = 0;
   out_1374196726603914191[48] = 0;
   out_1374196726603914191[49] = 0;
   out_1374196726603914191[50] = 0;
   out_1374196726603914191[51] = 0;
   out_1374196726603914191[52] = 0;
   out_1374196726603914191[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_6908032543271437367) {
  err_fun(nom_x, delta_x, out_6908032543271437367);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6322019134835395929) {
  inv_err_fun(nom_x, true_x, out_6322019134835395929);
}
void pose_H_mod_fun(double *state, double *out_5045397248752443787) {
  H_mod_fun(state, out_5045397248752443787);
}
void pose_f_fun(double *state, double dt, double *out_2578103679579667045) {
  f_fun(state,  dt, out_2578103679579667045);
}
void pose_F_fun(double *state, double dt, double *out_9023639176273047325) {
  F_fun(state,  dt, out_9023639176273047325);
}
void pose_h_4(double *state, double *unused, double *out_6773770520031459625) {
  h_4(state, unused, out_6773770520031459625);
}
void pose_H_4(double *state, double *unused, double *out_4456985158899286487) {
  H_4(state, unused, out_4456985158899286487);
}
void pose_h_10(double *state, double *unused, double *out_2891796970203767629) {
  h_10(state, unused, out_2891796970203767629);
}
void pose_H_10(double *state, double *unused, double *out_5240016567730035669) {
  H_10(state, unused, out_5240016567730035669);
}
void pose_h_13(double *state, double *unused, double *out_7766623268738295305) {
  h_13(state, unused, out_7766623268738295305);
}
void pose_H_13(double *state, double *unused, double *out_623229695596762463) {
  H_13(state, unused, out_623229695596762463);
}
void pose_h_14(double *state, double *unused, double *out_3433693932581315158) {
  h_14(state, unused, out_3433693932581315158);
}
void pose_H_14(double *state, double *unused, double *out_1374196726603914191) {
  H_14(state, unused, out_1374196726603914191);
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
