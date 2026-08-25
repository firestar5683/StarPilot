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
void err_fun(double *nom_x, double *delta_x, double *out_7562252914855705934) {
   out_7562252914855705934[0] = delta_x[0] + nom_x[0];
   out_7562252914855705934[1] = delta_x[1] + nom_x[1];
   out_7562252914855705934[2] = delta_x[2] + nom_x[2];
   out_7562252914855705934[3] = delta_x[3] + nom_x[3];
   out_7562252914855705934[4] = delta_x[4] + nom_x[4];
   out_7562252914855705934[5] = delta_x[5] + nom_x[5];
   out_7562252914855705934[6] = delta_x[6] + nom_x[6];
   out_7562252914855705934[7] = delta_x[7] + nom_x[7];
   out_7562252914855705934[8] = delta_x[8] + nom_x[8];
   out_7562252914855705934[9] = delta_x[9] + nom_x[9];
   out_7562252914855705934[10] = delta_x[10] + nom_x[10];
   out_7562252914855705934[11] = delta_x[11] + nom_x[11];
   out_7562252914855705934[12] = delta_x[12] + nom_x[12];
   out_7562252914855705934[13] = delta_x[13] + nom_x[13];
   out_7562252914855705934[14] = delta_x[14] + nom_x[14];
   out_7562252914855705934[15] = delta_x[15] + nom_x[15];
   out_7562252914855705934[16] = delta_x[16] + nom_x[16];
   out_7562252914855705934[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7624660990393256492) {
   out_7624660990393256492[0] = -nom_x[0] + true_x[0];
   out_7624660990393256492[1] = -nom_x[1] + true_x[1];
   out_7624660990393256492[2] = -nom_x[2] + true_x[2];
   out_7624660990393256492[3] = -nom_x[3] + true_x[3];
   out_7624660990393256492[4] = -nom_x[4] + true_x[4];
   out_7624660990393256492[5] = -nom_x[5] + true_x[5];
   out_7624660990393256492[6] = -nom_x[6] + true_x[6];
   out_7624660990393256492[7] = -nom_x[7] + true_x[7];
   out_7624660990393256492[8] = -nom_x[8] + true_x[8];
   out_7624660990393256492[9] = -nom_x[9] + true_x[9];
   out_7624660990393256492[10] = -nom_x[10] + true_x[10];
   out_7624660990393256492[11] = -nom_x[11] + true_x[11];
   out_7624660990393256492[12] = -nom_x[12] + true_x[12];
   out_7624660990393256492[13] = -nom_x[13] + true_x[13];
   out_7624660990393256492[14] = -nom_x[14] + true_x[14];
   out_7624660990393256492[15] = -nom_x[15] + true_x[15];
   out_7624660990393256492[16] = -nom_x[16] + true_x[16];
   out_7624660990393256492[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_4788463691933235788) {
   out_4788463691933235788[0] = 1.0;
   out_4788463691933235788[1] = 0.0;
   out_4788463691933235788[2] = 0.0;
   out_4788463691933235788[3] = 0.0;
   out_4788463691933235788[4] = 0.0;
   out_4788463691933235788[5] = 0.0;
   out_4788463691933235788[6] = 0.0;
   out_4788463691933235788[7] = 0.0;
   out_4788463691933235788[8] = 0.0;
   out_4788463691933235788[9] = 0.0;
   out_4788463691933235788[10] = 0.0;
   out_4788463691933235788[11] = 0.0;
   out_4788463691933235788[12] = 0.0;
   out_4788463691933235788[13] = 0.0;
   out_4788463691933235788[14] = 0.0;
   out_4788463691933235788[15] = 0.0;
   out_4788463691933235788[16] = 0.0;
   out_4788463691933235788[17] = 0.0;
   out_4788463691933235788[18] = 0.0;
   out_4788463691933235788[19] = 1.0;
   out_4788463691933235788[20] = 0.0;
   out_4788463691933235788[21] = 0.0;
   out_4788463691933235788[22] = 0.0;
   out_4788463691933235788[23] = 0.0;
   out_4788463691933235788[24] = 0.0;
   out_4788463691933235788[25] = 0.0;
   out_4788463691933235788[26] = 0.0;
   out_4788463691933235788[27] = 0.0;
   out_4788463691933235788[28] = 0.0;
   out_4788463691933235788[29] = 0.0;
   out_4788463691933235788[30] = 0.0;
   out_4788463691933235788[31] = 0.0;
   out_4788463691933235788[32] = 0.0;
   out_4788463691933235788[33] = 0.0;
   out_4788463691933235788[34] = 0.0;
   out_4788463691933235788[35] = 0.0;
   out_4788463691933235788[36] = 0.0;
   out_4788463691933235788[37] = 0.0;
   out_4788463691933235788[38] = 1.0;
   out_4788463691933235788[39] = 0.0;
   out_4788463691933235788[40] = 0.0;
   out_4788463691933235788[41] = 0.0;
   out_4788463691933235788[42] = 0.0;
   out_4788463691933235788[43] = 0.0;
   out_4788463691933235788[44] = 0.0;
   out_4788463691933235788[45] = 0.0;
   out_4788463691933235788[46] = 0.0;
   out_4788463691933235788[47] = 0.0;
   out_4788463691933235788[48] = 0.0;
   out_4788463691933235788[49] = 0.0;
   out_4788463691933235788[50] = 0.0;
   out_4788463691933235788[51] = 0.0;
   out_4788463691933235788[52] = 0.0;
   out_4788463691933235788[53] = 0.0;
   out_4788463691933235788[54] = 0.0;
   out_4788463691933235788[55] = 0.0;
   out_4788463691933235788[56] = 0.0;
   out_4788463691933235788[57] = 1.0;
   out_4788463691933235788[58] = 0.0;
   out_4788463691933235788[59] = 0.0;
   out_4788463691933235788[60] = 0.0;
   out_4788463691933235788[61] = 0.0;
   out_4788463691933235788[62] = 0.0;
   out_4788463691933235788[63] = 0.0;
   out_4788463691933235788[64] = 0.0;
   out_4788463691933235788[65] = 0.0;
   out_4788463691933235788[66] = 0.0;
   out_4788463691933235788[67] = 0.0;
   out_4788463691933235788[68] = 0.0;
   out_4788463691933235788[69] = 0.0;
   out_4788463691933235788[70] = 0.0;
   out_4788463691933235788[71] = 0.0;
   out_4788463691933235788[72] = 0.0;
   out_4788463691933235788[73] = 0.0;
   out_4788463691933235788[74] = 0.0;
   out_4788463691933235788[75] = 0.0;
   out_4788463691933235788[76] = 1.0;
   out_4788463691933235788[77] = 0.0;
   out_4788463691933235788[78] = 0.0;
   out_4788463691933235788[79] = 0.0;
   out_4788463691933235788[80] = 0.0;
   out_4788463691933235788[81] = 0.0;
   out_4788463691933235788[82] = 0.0;
   out_4788463691933235788[83] = 0.0;
   out_4788463691933235788[84] = 0.0;
   out_4788463691933235788[85] = 0.0;
   out_4788463691933235788[86] = 0.0;
   out_4788463691933235788[87] = 0.0;
   out_4788463691933235788[88] = 0.0;
   out_4788463691933235788[89] = 0.0;
   out_4788463691933235788[90] = 0.0;
   out_4788463691933235788[91] = 0.0;
   out_4788463691933235788[92] = 0.0;
   out_4788463691933235788[93] = 0.0;
   out_4788463691933235788[94] = 0.0;
   out_4788463691933235788[95] = 1.0;
   out_4788463691933235788[96] = 0.0;
   out_4788463691933235788[97] = 0.0;
   out_4788463691933235788[98] = 0.0;
   out_4788463691933235788[99] = 0.0;
   out_4788463691933235788[100] = 0.0;
   out_4788463691933235788[101] = 0.0;
   out_4788463691933235788[102] = 0.0;
   out_4788463691933235788[103] = 0.0;
   out_4788463691933235788[104] = 0.0;
   out_4788463691933235788[105] = 0.0;
   out_4788463691933235788[106] = 0.0;
   out_4788463691933235788[107] = 0.0;
   out_4788463691933235788[108] = 0.0;
   out_4788463691933235788[109] = 0.0;
   out_4788463691933235788[110] = 0.0;
   out_4788463691933235788[111] = 0.0;
   out_4788463691933235788[112] = 0.0;
   out_4788463691933235788[113] = 0.0;
   out_4788463691933235788[114] = 1.0;
   out_4788463691933235788[115] = 0.0;
   out_4788463691933235788[116] = 0.0;
   out_4788463691933235788[117] = 0.0;
   out_4788463691933235788[118] = 0.0;
   out_4788463691933235788[119] = 0.0;
   out_4788463691933235788[120] = 0.0;
   out_4788463691933235788[121] = 0.0;
   out_4788463691933235788[122] = 0.0;
   out_4788463691933235788[123] = 0.0;
   out_4788463691933235788[124] = 0.0;
   out_4788463691933235788[125] = 0.0;
   out_4788463691933235788[126] = 0.0;
   out_4788463691933235788[127] = 0.0;
   out_4788463691933235788[128] = 0.0;
   out_4788463691933235788[129] = 0.0;
   out_4788463691933235788[130] = 0.0;
   out_4788463691933235788[131] = 0.0;
   out_4788463691933235788[132] = 0.0;
   out_4788463691933235788[133] = 1.0;
   out_4788463691933235788[134] = 0.0;
   out_4788463691933235788[135] = 0.0;
   out_4788463691933235788[136] = 0.0;
   out_4788463691933235788[137] = 0.0;
   out_4788463691933235788[138] = 0.0;
   out_4788463691933235788[139] = 0.0;
   out_4788463691933235788[140] = 0.0;
   out_4788463691933235788[141] = 0.0;
   out_4788463691933235788[142] = 0.0;
   out_4788463691933235788[143] = 0.0;
   out_4788463691933235788[144] = 0.0;
   out_4788463691933235788[145] = 0.0;
   out_4788463691933235788[146] = 0.0;
   out_4788463691933235788[147] = 0.0;
   out_4788463691933235788[148] = 0.0;
   out_4788463691933235788[149] = 0.0;
   out_4788463691933235788[150] = 0.0;
   out_4788463691933235788[151] = 0.0;
   out_4788463691933235788[152] = 1.0;
   out_4788463691933235788[153] = 0.0;
   out_4788463691933235788[154] = 0.0;
   out_4788463691933235788[155] = 0.0;
   out_4788463691933235788[156] = 0.0;
   out_4788463691933235788[157] = 0.0;
   out_4788463691933235788[158] = 0.0;
   out_4788463691933235788[159] = 0.0;
   out_4788463691933235788[160] = 0.0;
   out_4788463691933235788[161] = 0.0;
   out_4788463691933235788[162] = 0.0;
   out_4788463691933235788[163] = 0.0;
   out_4788463691933235788[164] = 0.0;
   out_4788463691933235788[165] = 0.0;
   out_4788463691933235788[166] = 0.0;
   out_4788463691933235788[167] = 0.0;
   out_4788463691933235788[168] = 0.0;
   out_4788463691933235788[169] = 0.0;
   out_4788463691933235788[170] = 0.0;
   out_4788463691933235788[171] = 1.0;
   out_4788463691933235788[172] = 0.0;
   out_4788463691933235788[173] = 0.0;
   out_4788463691933235788[174] = 0.0;
   out_4788463691933235788[175] = 0.0;
   out_4788463691933235788[176] = 0.0;
   out_4788463691933235788[177] = 0.0;
   out_4788463691933235788[178] = 0.0;
   out_4788463691933235788[179] = 0.0;
   out_4788463691933235788[180] = 0.0;
   out_4788463691933235788[181] = 0.0;
   out_4788463691933235788[182] = 0.0;
   out_4788463691933235788[183] = 0.0;
   out_4788463691933235788[184] = 0.0;
   out_4788463691933235788[185] = 0.0;
   out_4788463691933235788[186] = 0.0;
   out_4788463691933235788[187] = 0.0;
   out_4788463691933235788[188] = 0.0;
   out_4788463691933235788[189] = 0.0;
   out_4788463691933235788[190] = 1.0;
   out_4788463691933235788[191] = 0.0;
   out_4788463691933235788[192] = 0.0;
   out_4788463691933235788[193] = 0.0;
   out_4788463691933235788[194] = 0.0;
   out_4788463691933235788[195] = 0.0;
   out_4788463691933235788[196] = 0.0;
   out_4788463691933235788[197] = 0.0;
   out_4788463691933235788[198] = 0.0;
   out_4788463691933235788[199] = 0.0;
   out_4788463691933235788[200] = 0.0;
   out_4788463691933235788[201] = 0.0;
   out_4788463691933235788[202] = 0.0;
   out_4788463691933235788[203] = 0.0;
   out_4788463691933235788[204] = 0.0;
   out_4788463691933235788[205] = 0.0;
   out_4788463691933235788[206] = 0.0;
   out_4788463691933235788[207] = 0.0;
   out_4788463691933235788[208] = 0.0;
   out_4788463691933235788[209] = 1.0;
   out_4788463691933235788[210] = 0.0;
   out_4788463691933235788[211] = 0.0;
   out_4788463691933235788[212] = 0.0;
   out_4788463691933235788[213] = 0.0;
   out_4788463691933235788[214] = 0.0;
   out_4788463691933235788[215] = 0.0;
   out_4788463691933235788[216] = 0.0;
   out_4788463691933235788[217] = 0.0;
   out_4788463691933235788[218] = 0.0;
   out_4788463691933235788[219] = 0.0;
   out_4788463691933235788[220] = 0.0;
   out_4788463691933235788[221] = 0.0;
   out_4788463691933235788[222] = 0.0;
   out_4788463691933235788[223] = 0.0;
   out_4788463691933235788[224] = 0.0;
   out_4788463691933235788[225] = 0.0;
   out_4788463691933235788[226] = 0.0;
   out_4788463691933235788[227] = 0.0;
   out_4788463691933235788[228] = 1.0;
   out_4788463691933235788[229] = 0.0;
   out_4788463691933235788[230] = 0.0;
   out_4788463691933235788[231] = 0.0;
   out_4788463691933235788[232] = 0.0;
   out_4788463691933235788[233] = 0.0;
   out_4788463691933235788[234] = 0.0;
   out_4788463691933235788[235] = 0.0;
   out_4788463691933235788[236] = 0.0;
   out_4788463691933235788[237] = 0.0;
   out_4788463691933235788[238] = 0.0;
   out_4788463691933235788[239] = 0.0;
   out_4788463691933235788[240] = 0.0;
   out_4788463691933235788[241] = 0.0;
   out_4788463691933235788[242] = 0.0;
   out_4788463691933235788[243] = 0.0;
   out_4788463691933235788[244] = 0.0;
   out_4788463691933235788[245] = 0.0;
   out_4788463691933235788[246] = 0.0;
   out_4788463691933235788[247] = 1.0;
   out_4788463691933235788[248] = 0.0;
   out_4788463691933235788[249] = 0.0;
   out_4788463691933235788[250] = 0.0;
   out_4788463691933235788[251] = 0.0;
   out_4788463691933235788[252] = 0.0;
   out_4788463691933235788[253] = 0.0;
   out_4788463691933235788[254] = 0.0;
   out_4788463691933235788[255] = 0.0;
   out_4788463691933235788[256] = 0.0;
   out_4788463691933235788[257] = 0.0;
   out_4788463691933235788[258] = 0.0;
   out_4788463691933235788[259] = 0.0;
   out_4788463691933235788[260] = 0.0;
   out_4788463691933235788[261] = 0.0;
   out_4788463691933235788[262] = 0.0;
   out_4788463691933235788[263] = 0.0;
   out_4788463691933235788[264] = 0.0;
   out_4788463691933235788[265] = 0.0;
   out_4788463691933235788[266] = 1.0;
   out_4788463691933235788[267] = 0.0;
   out_4788463691933235788[268] = 0.0;
   out_4788463691933235788[269] = 0.0;
   out_4788463691933235788[270] = 0.0;
   out_4788463691933235788[271] = 0.0;
   out_4788463691933235788[272] = 0.0;
   out_4788463691933235788[273] = 0.0;
   out_4788463691933235788[274] = 0.0;
   out_4788463691933235788[275] = 0.0;
   out_4788463691933235788[276] = 0.0;
   out_4788463691933235788[277] = 0.0;
   out_4788463691933235788[278] = 0.0;
   out_4788463691933235788[279] = 0.0;
   out_4788463691933235788[280] = 0.0;
   out_4788463691933235788[281] = 0.0;
   out_4788463691933235788[282] = 0.0;
   out_4788463691933235788[283] = 0.0;
   out_4788463691933235788[284] = 0.0;
   out_4788463691933235788[285] = 1.0;
   out_4788463691933235788[286] = 0.0;
   out_4788463691933235788[287] = 0.0;
   out_4788463691933235788[288] = 0.0;
   out_4788463691933235788[289] = 0.0;
   out_4788463691933235788[290] = 0.0;
   out_4788463691933235788[291] = 0.0;
   out_4788463691933235788[292] = 0.0;
   out_4788463691933235788[293] = 0.0;
   out_4788463691933235788[294] = 0.0;
   out_4788463691933235788[295] = 0.0;
   out_4788463691933235788[296] = 0.0;
   out_4788463691933235788[297] = 0.0;
   out_4788463691933235788[298] = 0.0;
   out_4788463691933235788[299] = 0.0;
   out_4788463691933235788[300] = 0.0;
   out_4788463691933235788[301] = 0.0;
   out_4788463691933235788[302] = 0.0;
   out_4788463691933235788[303] = 0.0;
   out_4788463691933235788[304] = 1.0;
   out_4788463691933235788[305] = 0.0;
   out_4788463691933235788[306] = 0.0;
   out_4788463691933235788[307] = 0.0;
   out_4788463691933235788[308] = 0.0;
   out_4788463691933235788[309] = 0.0;
   out_4788463691933235788[310] = 0.0;
   out_4788463691933235788[311] = 0.0;
   out_4788463691933235788[312] = 0.0;
   out_4788463691933235788[313] = 0.0;
   out_4788463691933235788[314] = 0.0;
   out_4788463691933235788[315] = 0.0;
   out_4788463691933235788[316] = 0.0;
   out_4788463691933235788[317] = 0.0;
   out_4788463691933235788[318] = 0.0;
   out_4788463691933235788[319] = 0.0;
   out_4788463691933235788[320] = 0.0;
   out_4788463691933235788[321] = 0.0;
   out_4788463691933235788[322] = 0.0;
   out_4788463691933235788[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_278833928334043643) {
   out_278833928334043643[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_278833928334043643[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_278833928334043643[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_278833928334043643[3] = dt*state[12] + state[3];
   out_278833928334043643[4] = dt*state[13] + state[4];
   out_278833928334043643[5] = dt*state[14] + state[5];
   out_278833928334043643[6] = state[6];
   out_278833928334043643[7] = state[7];
   out_278833928334043643[8] = state[8];
   out_278833928334043643[9] = state[9];
   out_278833928334043643[10] = state[10];
   out_278833928334043643[11] = state[11];
   out_278833928334043643[12] = state[12];
   out_278833928334043643[13] = state[13];
   out_278833928334043643[14] = state[14];
   out_278833928334043643[15] = state[15];
   out_278833928334043643[16] = state[16];
   out_278833928334043643[17] = state[17];
}
void F_fun(double *state, double dt, double *out_4640315684238237796) {
   out_4640315684238237796[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4640315684238237796[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4640315684238237796[2] = 0;
   out_4640315684238237796[3] = 0;
   out_4640315684238237796[4] = 0;
   out_4640315684238237796[5] = 0;
   out_4640315684238237796[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4640315684238237796[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4640315684238237796[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4640315684238237796[9] = 0;
   out_4640315684238237796[10] = 0;
   out_4640315684238237796[11] = 0;
   out_4640315684238237796[12] = 0;
   out_4640315684238237796[13] = 0;
   out_4640315684238237796[14] = 0;
   out_4640315684238237796[15] = 0;
   out_4640315684238237796[16] = 0;
   out_4640315684238237796[17] = 0;
   out_4640315684238237796[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4640315684238237796[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4640315684238237796[20] = 0;
   out_4640315684238237796[21] = 0;
   out_4640315684238237796[22] = 0;
   out_4640315684238237796[23] = 0;
   out_4640315684238237796[24] = 0;
   out_4640315684238237796[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4640315684238237796[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4640315684238237796[27] = 0;
   out_4640315684238237796[28] = 0;
   out_4640315684238237796[29] = 0;
   out_4640315684238237796[30] = 0;
   out_4640315684238237796[31] = 0;
   out_4640315684238237796[32] = 0;
   out_4640315684238237796[33] = 0;
   out_4640315684238237796[34] = 0;
   out_4640315684238237796[35] = 0;
   out_4640315684238237796[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4640315684238237796[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4640315684238237796[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4640315684238237796[39] = 0;
   out_4640315684238237796[40] = 0;
   out_4640315684238237796[41] = 0;
   out_4640315684238237796[42] = 0;
   out_4640315684238237796[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4640315684238237796[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4640315684238237796[45] = 0;
   out_4640315684238237796[46] = 0;
   out_4640315684238237796[47] = 0;
   out_4640315684238237796[48] = 0;
   out_4640315684238237796[49] = 0;
   out_4640315684238237796[50] = 0;
   out_4640315684238237796[51] = 0;
   out_4640315684238237796[52] = 0;
   out_4640315684238237796[53] = 0;
   out_4640315684238237796[54] = 0;
   out_4640315684238237796[55] = 0;
   out_4640315684238237796[56] = 0;
   out_4640315684238237796[57] = 1;
   out_4640315684238237796[58] = 0;
   out_4640315684238237796[59] = 0;
   out_4640315684238237796[60] = 0;
   out_4640315684238237796[61] = 0;
   out_4640315684238237796[62] = 0;
   out_4640315684238237796[63] = 0;
   out_4640315684238237796[64] = 0;
   out_4640315684238237796[65] = 0;
   out_4640315684238237796[66] = dt;
   out_4640315684238237796[67] = 0;
   out_4640315684238237796[68] = 0;
   out_4640315684238237796[69] = 0;
   out_4640315684238237796[70] = 0;
   out_4640315684238237796[71] = 0;
   out_4640315684238237796[72] = 0;
   out_4640315684238237796[73] = 0;
   out_4640315684238237796[74] = 0;
   out_4640315684238237796[75] = 0;
   out_4640315684238237796[76] = 1;
   out_4640315684238237796[77] = 0;
   out_4640315684238237796[78] = 0;
   out_4640315684238237796[79] = 0;
   out_4640315684238237796[80] = 0;
   out_4640315684238237796[81] = 0;
   out_4640315684238237796[82] = 0;
   out_4640315684238237796[83] = 0;
   out_4640315684238237796[84] = 0;
   out_4640315684238237796[85] = dt;
   out_4640315684238237796[86] = 0;
   out_4640315684238237796[87] = 0;
   out_4640315684238237796[88] = 0;
   out_4640315684238237796[89] = 0;
   out_4640315684238237796[90] = 0;
   out_4640315684238237796[91] = 0;
   out_4640315684238237796[92] = 0;
   out_4640315684238237796[93] = 0;
   out_4640315684238237796[94] = 0;
   out_4640315684238237796[95] = 1;
   out_4640315684238237796[96] = 0;
   out_4640315684238237796[97] = 0;
   out_4640315684238237796[98] = 0;
   out_4640315684238237796[99] = 0;
   out_4640315684238237796[100] = 0;
   out_4640315684238237796[101] = 0;
   out_4640315684238237796[102] = 0;
   out_4640315684238237796[103] = 0;
   out_4640315684238237796[104] = dt;
   out_4640315684238237796[105] = 0;
   out_4640315684238237796[106] = 0;
   out_4640315684238237796[107] = 0;
   out_4640315684238237796[108] = 0;
   out_4640315684238237796[109] = 0;
   out_4640315684238237796[110] = 0;
   out_4640315684238237796[111] = 0;
   out_4640315684238237796[112] = 0;
   out_4640315684238237796[113] = 0;
   out_4640315684238237796[114] = 1;
   out_4640315684238237796[115] = 0;
   out_4640315684238237796[116] = 0;
   out_4640315684238237796[117] = 0;
   out_4640315684238237796[118] = 0;
   out_4640315684238237796[119] = 0;
   out_4640315684238237796[120] = 0;
   out_4640315684238237796[121] = 0;
   out_4640315684238237796[122] = 0;
   out_4640315684238237796[123] = 0;
   out_4640315684238237796[124] = 0;
   out_4640315684238237796[125] = 0;
   out_4640315684238237796[126] = 0;
   out_4640315684238237796[127] = 0;
   out_4640315684238237796[128] = 0;
   out_4640315684238237796[129] = 0;
   out_4640315684238237796[130] = 0;
   out_4640315684238237796[131] = 0;
   out_4640315684238237796[132] = 0;
   out_4640315684238237796[133] = 1;
   out_4640315684238237796[134] = 0;
   out_4640315684238237796[135] = 0;
   out_4640315684238237796[136] = 0;
   out_4640315684238237796[137] = 0;
   out_4640315684238237796[138] = 0;
   out_4640315684238237796[139] = 0;
   out_4640315684238237796[140] = 0;
   out_4640315684238237796[141] = 0;
   out_4640315684238237796[142] = 0;
   out_4640315684238237796[143] = 0;
   out_4640315684238237796[144] = 0;
   out_4640315684238237796[145] = 0;
   out_4640315684238237796[146] = 0;
   out_4640315684238237796[147] = 0;
   out_4640315684238237796[148] = 0;
   out_4640315684238237796[149] = 0;
   out_4640315684238237796[150] = 0;
   out_4640315684238237796[151] = 0;
   out_4640315684238237796[152] = 1;
   out_4640315684238237796[153] = 0;
   out_4640315684238237796[154] = 0;
   out_4640315684238237796[155] = 0;
   out_4640315684238237796[156] = 0;
   out_4640315684238237796[157] = 0;
   out_4640315684238237796[158] = 0;
   out_4640315684238237796[159] = 0;
   out_4640315684238237796[160] = 0;
   out_4640315684238237796[161] = 0;
   out_4640315684238237796[162] = 0;
   out_4640315684238237796[163] = 0;
   out_4640315684238237796[164] = 0;
   out_4640315684238237796[165] = 0;
   out_4640315684238237796[166] = 0;
   out_4640315684238237796[167] = 0;
   out_4640315684238237796[168] = 0;
   out_4640315684238237796[169] = 0;
   out_4640315684238237796[170] = 0;
   out_4640315684238237796[171] = 1;
   out_4640315684238237796[172] = 0;
   out_4640315684238237796[173] = 0;
   out_4640315684238237796[174] = 0;
   out_4640315684238237796[175] = 0;
   out_4640315684238237796[176] = 0;
   out_4640315684238237796[177] = 0;
   out_4640315684238237796[178] = 0;
   out_4640315684238237796[179] = 0;
   out_4640315684238237796[180] = 0;
   out_4640315684238237796[181] = 0;
   out_4640315684238237796[182] = 0;
   out_4640315684238237796[183] = 0;
   out_4640315684238237796[184] = 0;
   out_4640315684238237796[185] = 0;
   out_4640315684238237796[186] = 0;
   out_4640315684238237796[187] = 0;
   out_4640315684238237796[188] = 0;
   out_4640315684238237796[189] = 0;
   out_4640315684238237796[190] = 1;
   out_4640315684238237796[191] = 0;
   out_4640315684238237796[192] = 0;
   out_4640315684238237796[193] = 0;
   out_4640315684238237796[194] = 0;
   out_4640315684238237796[195] = 0;
   out_4640315684238237796[196] = 0;
   out_4640315684238237796[197] = 0;
   out_4640315684238237796[198] = 0;
   out_4640315684238237796[199] = 0;
   out_4640315684238237796[200] = 0;
   out_4640315684238237796[201] = 0;
   out_4640315684238237796[202] = 0;
   out_4640315684238237796[203] = 0;
   out_4640315684238237796[204] = 0;
   out_4640315684238237796[205] = 0;
   out_4640315684238237796[206] = 0;
   out_4640315684238237796[207] = 0;
   out_4640315684238237796[208] = 0;
   out_4640315684238237796[209] = 1;
   out_4640315684238237796[210] = 0;
   out_4640315684238237796[211] = 0;
   out_4640315684238237796[212] = 0;
   out_4640315684238237796[213] = 0;
   out_4640315684238237796[214] = 0;
   out_4640315684238237796[215] = 0;
   out_4640315684238237796[216] = 0;
   out_4640315684238237796[217] = 0;
   out_4640315684238237796[218] = 0;
   out_4640315684238237796[219] = 0;
   out_4640315684238237796[220] = 0;
   out_4640315684238237796[221] = 0;
   out_4640315684238237796[222] = 0;
   out_4640315684238237796[223] = 0;
   out_4640315684238237796[224] = 0;
   out_4640315684238237796[225] = 0;
   out_4640315684238237796[226] = 0;
   out_4640315684238237796[227] = 0;
   out_4640315684238237796[228] = 1;
   out_4640315684238237796[229] = 0;
   out_4640315684238237796[230] = 0;
   out_4640315684238237796[231] = 0;
   out_4640315684238237796[232] = 0;
   out_4640315684238237796[233] = 0;
   out_4640315684238237796[234] = 0;
   out_4640315684238237796[235] = 0;
   out_4640315684238237796[236] = 0;
   out_4640315684238237796[237] = 0;
   out_4640315684238237796[238] = 0;
   out_4640315684238237796[239] = 0;
   out_4640315684238237796[240] = 0;
   out_4640315684238237796[241] = 0;
   out_4640315684238237796[242] = 0;
   out_4640315684238237796[243] = 0;
   out_4640315684238237796[244] = 0;
   out_4640315684238237796[245] = 0;
   out_4640315684238237796[246] = 0;
   out_4640315684238237796[247] = 1;
   out_4640315684238237796[248] = 0;
   out_4640315684238237796[249] = 0;
   out_4640315684238237796[250] = 0;
   out_4640315684238237796[251] = 0;
   out_4640315684238237796[252] = 0;
   out_4640315684238237796[253] = 0;
   out_4640315684238237796[254] = 0;
   out_4640315684238237796[255] = 0;
   out_4640315684238237796[256] = 0;
   out_4640315684238237796[257] = 0;
   out_4640315684238237796[258] = 0;
   out_4640315684238237796[259] = 0;
   out_4640315684238237796[260] = 0;
   out_4640315684238237796[261] = 0;
   out_4640315684238237796[262] = 0;
   out_4640315684238237796[263] = 0;
   out_4640315684238237796[264] = 0;
   out_4640315684238237796[265] = 0;
   out_4640315684238237796[266] = 1;
   out_4640315684238237796[267] = 0;
   out_4640315684238237796[268] = 0;
   out_4640315684238237796[269] = 0;
   out_4640315684238237796[270] = 0;
   out_4640315684238237796[271] = 0;
   out_4640315684238237796[272] = 0;
   out_4640315684238237796[273] = 0;
   out_4640315684238237796[274] = 0;
   out_4640315684238237796[275] = 0;
   out_4640315684238237796[276] = 0;
   out_4640315684238237796[277] = 0;
   out_4640315684238237796[278] = 0;
   out_4640315684238237796[279] = 0;
   out_4640315684238237796[280] = 0;
   out_4640315684238237796[281] = 0;
   out_4640315684238237796[282] = 0;
   out_4640315684238237796[283] = 0;
   out_4640315684238237796[284] = 0;
   out_4640315684238237796[285] = 1;
   out_4640315684238237796[286] = 0;
   out_4640315684238237796[287] = 0;
   out_4640315684238237796[288] = 0;
   out_4640315684238237796[289] = 0;
   out_4640315684238237796[290] = 0;
   out_4640315684238237796[291] = 0;
   out_4640315684238237796[292] = 0;
   out_4640315684238237796[293] = 0;
   out_4640315684238237796[294] = 0;
   out_4640315684238237796[295] = 0;
   out_4640315684238237796[296] = 0;
   out_4640315684238237796[297] = 0;
   out_4640315684238237796[298] = 0;
   out_4640315684238237796[299] = 0;
   out_4640315684238237796[300] = 0;
   out_4640315684238237796[301] = 0;
   out_4640315684238237796[302] = 0;
   out_4640315684238237796[303] = 0;
   out_4640315684238237796[304] = 1;
   out_4640315684238237796[305] = 0;
   out_4640315684238237796[306] = 0;
   out_4640315684238237796[307] = 0;
   out_4640315684238237796[308] = 0;
   out_4640315684238237796[309] = 0;
   out_4640315684238237796[310] = 0;
   out_4640315684238237796[311] = 0;
   out_4640315684238237796[312] = 0;
   out_4640315684238237796[313] = 0;
   out_4640315684238237796[314] = 0;
   out_4640315684238237796[315] = 0;
   out_4640315684238237796[316] = 0;
   out_4640315684238237796[317] = 0;
   out_4640315684238237796[318] = 0;
   out_4640315684238237796[319] = 0;
   out_4640315684238237796[320] = 0;
   out_4640315684238237796[321] = 0;
   out_4640315684238237796[322] = 0;
   out_4640315684238237796[323] = 1;
}
void h_4(double *state, double *unused, double *out_5623878395716679644) {
   out_5623878395716679644[0] = state[6] + state[9];
   out_5623878395716679644[1] = state[7] + state[10];
   out_5623878395716679644[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_2968764966026938927) {
   out_2968764966026938927[0] = 0;
   out_2968764966026938927[1] = 0;
   out_2968764966026938927[2] = 0;
   out_2968764966026938927[3] = 0;
   out_2968764966026938927[4] = 0;
   out_2968764966026938927[5] = 0;
   out_2968764966026938927[6] = 1;
   out_2968764966026938927[7] = 0;
   out_2968764966026938927[8] = 0;
   out_2968764966026938927[9] = 1;
   out_2968764966026938927[10] = 0;
   out_2968764966026938927[11] = 0;
   out_2968764966026938927[12] = 0;
   out_2968764966026938927[13] = 0;
   out_2968764966026938927[14] = 0;
   out_2968764966026938927[15] = 0;
   out_2968764966026938927[16] = 0;
   out_2968764966026938927[17] = 0;
   out_2968764966026938927[18] = 0;
   out_2968764966026938927[19] = 0;
   out_2968764966026938927[20] = 0;
   out_2968764966026938927[21] = 0;
   out_2968764966026938927[22] = 0;
   out_2968764966026938927[23] = 0;
   out_2968764966026938927[24] = 0;
   out_2968764966026938927[25] = 1;
   out_2968764966026938927[26] = 0;
   out_2968764966026938927[27] = 0;
   out_2968764966026938927[28] = 1;
   out_2968764966026938927[29] = 0;
   out_2968764966026938927[30] = 0;
   out_2968764966026938927[31] = 0;
   out_2968764966026938927[32] = 0;
   out_2968764966026938927[33] = 0;
   out_2968764966026938927[34] = 0;
   out_2968764966026938927[35] = 0;
   out_2968764966026938927[36] = 0;
   out_2968764966026938927[37] = 0;
   out_2968764966026938927[38] = 0;
   out_2968764966026938927[39] = 0;
   out_2968764966026938927[40] = 0;
   out_2968764966026938927[41] = 0;
   out_2968764966026938927[42] = 0;
   out_2968764966026938927[43] = 0;
   out_2968764966026938927[44] = 1;
   out_2968764966026938927[45] = 0;
   out_2968764966026938927[46] = 0;
   out_2968764966026938927[47] = 1;
   out_2968764966026938927[48] = 0;
   out_2968764966026938927[49] = 0;
   out_2968764966026938927[50] = 0;
   out_2968764966026938927[51] = 0;
   out_2968764966026938927[52] = 0;
   out_2968764966026938927[53] = 0;
}
void h_10(double *state, double *unused, double *out_1108484870937860123) {
   out_1108484870937860123[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_1108484870937860123[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_1108484870937860123[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_562715734289542272) {
   out_562715734289542272[0] = 0;
   out_562715734289542272[1] = 9.8100000000000005*cos(state[1]);
   out_562715734289542272[2] = 0;
   out_562715734289542272[3] = 0;
   out_562715734289542272[4] = -state[8];
   out_562715734289542272[5] = state[7];
   out_562715734289542272[6] = 0;
   out_562715734289542272[7] = state[5];
   out_562715734289542272[8] = -state[4];
   out_562715734289542272[9] = 0;
   out_562715734289542272[10] = 0;
   out_562715734289542272[11] = 0;
   out_562715734289542272[12] = 1;
   out_562715734289542272[13] = 0;
   out_562715734289542272[14] = 0;
   out_562715734289542272[15] = 1;
   out_562715734289542272[16] = 0;
   out_562715734289542272[17] = 0;
   out_562715734289542272[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_562715734289542272[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_562715734289542272[20] = 0;
   out_562715734289542272[21] = state[8];
   out_562715734289542272[22] = 0;
   out_562715734289542272[23] = -state[6];
   out_562715734289542272[24] = -state[5];
   out_562715734289542272[25] = 0;
   out_562715734289542272[26] = state[3];
   out_562715734289542272[27] = 0;
   out_562715734289542272[28] = 0;
   out_562715734289542272[29] = 0;
   out_562715734289542272[30] = 0;
   out_562715734289542272[31] = 1;
   out_562715734289542272[32] = 0;
   out_562715734289542272[33] = 0;
   out_562715734289542272[34] = 1;
   out_562715734289542272[35] = 0;
   out_562715734289542272[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_562715734289542272[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_562715734289542272[38] = 0;
   out_562715734289542272[39] = -state[7];
   out_562715734289542272[40] = state[6];
   out_562715734289542272[41] = 0;
   out_562715734289542272[42] = state[4];
   out_562715734289542272[43] = -state[3];
   out_562715734289542272[44] = 0;
   out_562715734289542272[45] = 0;
   out_562715734289542272[46] = 0;
   out_562715734289542272[47] = 0;
   out_562715734289542272[48] = 0;
   out_562715734289542272[49] = 0;
   out_562715734289542272[50] = 1;
   out_562715734289542272[51] = 0;
   out_562715734289542272[52] = 0;
   out_562715734289542272[53] = 1;
}
void h_13(double *state, double *unused, double *out_7517291163150813919) {
   out_7517291163150813919[0] = state[3];
   out_7517291163150813919[1] = state[4];
   out_7517291163150813919[2] = state[5];
}
void H_13(double *state, double *unused, double *out_6181038791359271728) {
   out_6181038791359271728[0] = 0;
   out_6181038791359271728[1] = 0;
   out_6181038791359271728[2] = 0;
   out_6181038791359271728[3] = 1;
   out_6181038791359271728[4] = 0;
   out_6181038791359271728[5] = 0;
   out_6181038791359271728[6] = 0;
   out_6181038791359271728[7] = 0;
   out_6181038791359271728[8] = 0;
   out_6181038791359271728[9] = 0;
   out_6181038791359271728[10] = 0;
   out_6181038791359271728[11] = 0;
   out_6181038791359271728[12] = 0;
   out_6181038791359271728[13] = 0;
   out_6181038791359271728[14] = 0;
   out_6181038791359271728[15] = 0;
   out_6181038791359271728[16] = 0;
   out_6181038791359271728[17] = 0;
   out_6181038791359271728[18] = 0;
   out_6181038791359271728[19] = 0;
   out_6181038791359271728[20] = 0;
   out_6181038791359271728[21] = 0;
   out_6181038791359271728[22] = 1;
   out_6181038791359271728[23] = 0;
   out_6181038791359271728[24] = 0;
   out_6181038791359271728[25] = 0;
   out_6181038791359271728[26] = 0;
   out_6181038791359271728[27] = 0;
   out_6181038791359271728[28] = 0;
   out_6181038791359271728[29] = 0;
   out_6181038791359271728[30] = 0;
   out_6181038791359271728[31] = 0;
   out_6181038791359271728[32] = 0;
   out_6181038791359271728[33] = 0;
   out_6181038791359271728[34] = 0;
   out_6181038791359271728[35] = 0;
   out_6181038791359271728[36] = 0;
   out_6181038791359271728[37] = 0;
   out_6181038791359271728[38] = 0;
   out_6181038791359271728[39] = 0;
   out_6181038791359271728[40] = 0;
   out_6181038791359271728[41] = 1;
   out_6181038791359271728[42] = 0;
   out_6181038791359271728[43] = 0;
   out_6181038791359271728[44] = 0;
   out_6181038791359271728[45] = 0;
   out_6181038791359271728[46] = 0;
   out_6181038791359271728[47] = 0;
   out_6181038791359271728[48] = 0;
   out_6181038791359271728[49] = 0;
   out_6181038791359271728[50] = 0;
   out_6181038791359271728[51] = 0;
   out_6181038791359271728[52] = 0;
   out_6181038791359271728[53] = 0;
}
void h_14(double *state, double *unused, double *out_7591297481791533481) {
   out_7591297481791533481[0] = state[6];
   out_7591297481791533481[1] = state[7];
   out_7591297481791533481[2] = state[8];
}
void H_14(double *state, double *unused, double *out_6932005822366423456) {
   out_6932005822366423456[0] = 0;
   out_6932005822366423456[1] = 0;
   out_6932005822366423456[2] = 0;
   out_6932005822366423456[3] = 0;
   out_6932005822366423456[4] = 0;
   out_6932005822366423456[5] = 0;
   out_6932005822366423456[6] = 1;
   out_6932005822366423456[7] = 0;
   out_6932005822366423456[8] = 0;
   out_6932005822366423456[9] = 0;
   out_6932005822366423456[10] = 0;
   out_6932005822366423456[11] = 0;
   out_6932005822366423456[12] = 0;
   out_6932005822366423456[13] = 0;
   out_6932005822366423456[14] = 0;
   out_6932005822366423456[15] = 0;
   out_6932005822366423456[16] = 0;
   out_6932005822366423456[17] = 0;
   out_6932005822366423456[18] = 0;
   out_6932005822366423456[19] = 0;
   out_6932005822366423456[20] = 0;
   out_6932005822366423456[21] = 0;
   out_6932005822366423456[22] = 0;
   out_6932005822366423456[23] = 0;
   out_6932005822366423456[24] = 0;
   out_6932005822366423456[25] = 1;
   out_6932005822366423456[26] = 0;
   out_6932005822366423456[27] = 0;
   out_6932005822366423456[28] = 0;
   out_6932005822366423456[29] = 0;
   out_6932005822366423456[30] = 0;
   out_6932005822366423456[31] = 0;
   out_6932005822366423456[32] = 0;
   out_6932005822366423456[33] = 0;
   out_6932005822366423456[34] = 0;
   out_6932005822366423456[35] = 0;
   out_6932005822366423456[36] = 0;
   out_6932005822366423456[37] = 0;
   out_6932005822366423456[38] = 0;
   out_6932005822366423456[39] = 0;
   out_6932005822366423456[40] = 0;
   out_6932005822366423456[41] = 0;
   out_6932005822366423456[42] = 0;
   out_6932005822366423456[43] = 0;
   out_6932005822366423456[44] = 1;
   out_6932005822366423456[45] = 0;
   out_6932005822366423456[46] = 0;
   out_6932005822366423456[47] = 0;
   out_6932005822366423456[48] = 0;
   out_6932005822366423456[49] = 0;
   out_6932005822366423456[50] = 0;
   out_6932005822366423456[51] = 0;
   out_6932005822366423456[52] = 0;
   out_6932005822366423456[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_7562252914855705934) {
  err_fun(nom_x, delta_x, out_7562252914855705934);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7624660990393256492) {
  inv_err_fun(nom_x, true_x, out_7624660990393256492);
}
void pose_H_mod_fun(double *state, double *out_4788463691933235788) {
  H_mod_fun(state, out_4788463691933235788);
}
void pose_f_fun(double *state, double dt, double *out_278833928334043643) {
  f_fun(state,  dt, out_278833928334043643);
}
void pose_F_fun(double *state, double dt, double *out_4640315684238237796) {
  F_fun(state,  dt, out_4640315684238237796);
}
void pose_h_4(double *state, double *unused, double *out_5623878395716679644) {
  h_4(state, unused, out_5623878395716679644);
}
void pose_H_4(double *state, double *unused, double *out_2968764966026938927) {
  H_4(state, unused, out_2968764966026938927);
}
void pose_h_10(double *state, double *unused, double *out_1108484870937860123) {
  h_10(state, unused, out_1108484870937860123);
}
void pose_H_10(double *state, double *unused, double *out_562715734289542272) {
  H_10(state, unused, out_562715734289542272);
}
void pose_h_13(double *state, double *unused, double *out_7517291163150813919) {
  h_13(state, unused, out_7517291163150813919);
}
void pose_H_13(double *state, double *unused, double *out_6181038791359271728) {
  H_13(state, unused, out_6181038791359271728);
}
void pose_h_14(double *state, double *unused, double *out_7591297481791533481) {
  h_14(state, unused, out_7591297481791533481);
}
void pose_H_14(double *state, double *unused, double *out_6932005822366423456) {
  H_14(state, unused, out_6932005822366423456);
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
